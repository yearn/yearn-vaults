// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import {Math} from "@openzeppelin/contracts/math/Math.sol";
import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";

import {VaultAPI} from "./BaseStrategy.sol";

interface RegistryAPI {
    function governance() external view returns (address);

    function latestVault(address token) external view returns (address);

    function nextDeployment(address token) external view returns (uint256);

    function vaults(address token, uint256 deploymentId) external view returns (address);
}

abstract contract BaseWrapper {
    using Math for uint256;
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    IERC20 public token;

    // Reduce number of external calls (SLOADs stay the same)
    VaultAPI[] private _cachedVaults;

    RegistryAPI public registry;

    constructor(address _token, address _registry) public {
        token = IERC20(_token);
        // v2.registry.ychad.eth
        registry = RegistryAPI(_registry);
    }

    function setRegistry(address _registry) external {
        require(msg.sender == registry.governance());
        // In case you want to override the registry instead of re-deploying
        registry = RegistryAPI(_registry);
    }

    function bestVault() public virtual view returns (VaultAPI) {
        return VaultAPI(registry.latestVault(address(token)));
    }

    function allVaults() public virtual view returns (VaultAPI[] memory) {
        uint256 cache_length = _cachedVaults.length;
        uint256 num_deployments = registry.nextDeployment(address(token));

        // Use cached
        if (cache_length == num_deployments) {
            return _cachedVaults;
        }

        VaultAPI[] memory vaults = new VaultAPI[](num_deployments);

        for (uint256 deployment_id = 0; deployment_id < cache_length; deployment_id++) {
            vaults[deployment_id] = _cachedVaults[deployment_id];
        }

        for (uint256 deployment_id = cache_length; deployment_id < num_deployments; deployment_id++) {
            vaults[deployment_id] = VaultAPI(registry.vaults(address(token), deployment_id));
        }

        return vaults;
    }

    function _updateVaultCache(VaultAPI[] memory vaults) internal {
        if (vaults.length > _cachedVaults.length) {
            _cachedVaults = vaults;
        }
    }

    function totalVaultBalance(address account) public view returns (uint256 balance) {
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            balance = balance.add(vaults[id].balanceOf(account).mul(vaults[id].pricePerShare()).div(10**uint256(vaults[id].decimals())));
        }
    }

    function totalAssets() public view returns (uint256 assets) {
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            assets = assets.add(vaults[id].totalAssets());
        }
    }

    function _deposit(
        address depositor,
        address receiver,
        uint256 amount,
        bool pullFunds // If true, funds need to be pulled from `depositor` via `transferFrom`
    ) internal returns (uint256) {
        VaultAPI _bestVault = bestVault();

        if (pullFunds) {
            token.safeTransferFrom(depositor, address(this), amount);
        }

        if (token.allowance(address(this), address(_bestVault)) < amount) {
            token.safeApprove(address(_bestVault), uint256(-1)); // Vaults are trusted
        }

        // `receiver` now has shares of `_bestVault` (worth `amount` tokens) as balance
        return
            _bestVault
                .deposit(amount, receiver)
                .mul(_bestVault.pricePerShare()) // Adjust by price of best
                .div(10**uint256(_bestVault.decimals()));
    }

    function _withdraw(
        address sender,
        address receiver,
        uint256 amount,
        bool withdrawFromBest // If true, also withdraw from _`bestVault`
    ) internal returns (uint256 withdrawn) {
        VaultAPI _bestVault = bestVault();

        VaultAPI[] memory vaults = allVaults();
        _updateVaultCache(vaults);

        for (uint256 id = 0; id < vaults.length; id++) {
            if (!withdrawFromBest && vaults[id] == _bestVault) {
                continue; // Don't withdraw from the best
            }

            // Start with the total shares that `sender` has
            uint256 availableShares = vaults[id].balanceOf(sender);

            // Restrict by the allowance that `sender` has to this contract
            // NOTE: No need for allowance check if `sender` is this contract
            if (sender != address(this)) {
                availableShares = Math.min(availableShares, vaults[id].allowance(sender, address(this)));
            }

            // Limit by maximum withdrawal size from each vault
            availableShares = Math.min(availableShares, vaults[id].maxAvailableShares());

            if (availableShares > 0) {
                // Compute amount to withdraw fully to satisfy the request
                uint256 shares = amount
                    .sub(withdrawn) // NOTE: Changes every iteration
                    .mul(10**uint256(vaults[id].decimals()))
                    .div(vaults[id].pricePerShare()); // NOTE: Every Vault is different

                // Limit amount to withdraw to the maximum made available to this contract
                shares = Math.min(shares, availableShares);

                // Intermediate step to move shares to this contract before withdrawing
                // NOTE: No need for share transfer if this contract is `sender`
                if (sender != address(this)) vaults[id].transferFrom(sender, address(this), shares);

                withdrawn = withdrawn.add(vaults[id].withdraw(shares, address(this)));

                // Check if we have fully satisfied the request
                // NOTE: use `amount = uint256(-1)` for withdrawing everything
                if (amount <= withdrawn) break; // withdrawn as much as we needed
            }
        }

        // If we have extra, deposit back into `_bestVault` for `sender`
        // NOTE: Invariant is `withdrawn <= amount`
        if (withdrawn > amount) {
            // Don't forget to approve the deposit
            if (token.allowance(address(this), address(_bestVault)) < withdrawn.sub(amount)) {
                token.safeApprove(address(_bestVault), uint256(-1)); // Vaults are trusted
            }

            _bestVault.deposit(withdrawn.sub(amount), sender);
            withdrawn = amount;
        }

        // `receiver` now has `withdrawn` tokens as balance
        if (receiver != address(this)) token.safeTransfer(receiver, withdrawn);
    }

    function _migrate(address account) internal returns (uint256) {
        return _migrate(account, totalVaultBalance(account));
    }

    function _migrate(address account, uint256 amount) internal returns (uint256 migrated) {
        // NOTE: In practice, it was discovered that <50 was the maximum we've see for this variance
        return _migrate(account, totalVaultBalance(account), 100);
    }

    function _migrate(
        address account,
        uint256 amount,
        uint256 maxMigrationLoss
    ) internal returns (uint256 migrated) {
        VaultAPI _bestVault = bestVault();

        uint256 alreadyDeposited = _bestVault.balanceOf(account).mul(_bestVault.pricePerShare()).div(10**uint256(_bestVault.decimals()));
        uint256 amountToMigrate = amount.sub(alreadyDeposited);

        uint256 depositLeft = _bestVault.depositLimit().sub(_bestVault.totalAssets());
        if (amountToMigrate > depositLeft) amountToMigrate = depositLeft;

        if (amountToMigrate > 0) {
            // NOTE: `false` = don't withdraw from `_bestVault`
            uint256 withdrawn = _withdraw(account, address(this), amountToMigrate, false);
            require(amountToMigrate.sub(withdrawn) <= maxMigrationLoss);
            // NOTE: `false` = don't do `transferFrom` because it's already local
            migrated = _deposit(address(this), account, withdrawn, false);
            // NOTE: Due to the precision loss of certain calculations, there is a small inefficency
            //       on how migrations are calculated, and this could lead to a DoS issue. Hence, this
            //       value is made to be configurable to allow the user to specify how much is acceptable
            require(withdrawn.sub(migrated) <= maxMigrationLoss);
        } // else: nothing to migrate! (not a failure)
    }
}
