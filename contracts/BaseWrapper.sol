// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";

import {RegistryAPI, VaultAPI} from "./BaseStrategy.sol";

abstract contract BaseWrapper {
    using SafeMath for uint256;

    ERC20 public token;

    // Reduce number of external calls (SLOADs stay the same)
    VaultAPI[] private _cachedVaults;

    RegistryAPI public registry;

    constructor(address _token, address _registry) public {
        token = ERC20(_token);
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
            assets = assets.add(vaults[id].totalAssets().mul(vaults[id].pricePerShare()).div(10**vaults[id].decimals()));
        }
    }

    function _deposit(
        address depositor,
        address reciever,
        uint256 amount,
        bool pullFunds // If true, funds need to be pulled from `depositor` via `transferFrom`
    ) internal returns (uint256) {
        VaultAPI best = bestVault();

        if (pullFunds) {
            token.transferFrom(depositor, address(this), amount);
        }

        if (token.allowance(address(this), address(best)) < amount) {
            token.approve(address(best), uint256(-1)); // Vaults are trusted
        }

        // `receiver` now has shares of `best` (worth `amount` tokens) as balance
        return
            best
                .deposit(amount, reciever)
                .mul(best.pricePerShare()) // Adjust by price of best
                .div(10**uint256(best.decimals()));
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return (a < b) ? a : b;
    }

    function _withdraw(
        address sender,
        address receiver,
        uint256 amount,
        bool withdrawFromBest // If true, also withdraw from `best`
    ) internal returns (uint256 withdrawn) {
        VaultAPI best = bestVault();

        VaultAPI[] memory vaults = allVaults();
        _updateVaultCache(vaults);

        for (uint256 id = 0; id < vaults.length; id++) {
            if (!withdrawFromBest && vaults[id] == best) {
                continue; // Don't withdraw from the best
            }

            // Start with the total shares that `sender` has
            uint256 availableShares = vaults[id].balanceOf(sender);

            // Restrict by the allowance that `sender` has to this contract
            // NOTE: No need for allowance check if `sender` is this contract
            if (sender != address(this)) {
                availableShares = min(availableShares, vaults[id].allowance(sender, address(this)));
            }

            // Limit by maximum withdrawal size from each vault
            availableShares = min(availableShares, vaults[id].maxAvailableShares());

            if (availableShares > 0) {
                // Compute amount to withdraw fully to satisfy the request
                uint256 shares = amount
                    .sub(withdrawn) // NOTE: Changes every iteration
                    .mul(10**uint256(vaults[id].decimals()))
                    .div(vaults[id].pricePerShare()); // NOTE: Every Vault is different

                // Limit amount to withdraw to the maximum made available to this contract
                shares = min(shares, availableShares);

                // Intermediate step to move shares to this contract before withdrawing
                // NOTE: No need for share transfer if this contract is `sender`
                if (sender != address(this)) vaults[id].transferFrom(sender, address(this), shares);

                withdrawn = withdrawn.add(vaults[id].withdraw(shares, address(this)));

                // Check if we have fully satisfied the request
                // NOTE: use `amount = uint256(-1)` for withdrawing everything
                if (amount <= withdrawn) break; // withdrawn as much as we needed
            }
        }

        // If we have extra, deposit back into `best` for `sender`
        // NOTE: Invariant is `withdrawn <= amount`
        if (withdrawn > amount) {
            // Don't forget to approve the deposit
            if (token.allowance(address(this), address(best)) < withdrawn.sub(amount)) {
                token.approve(address(best), uint256(-1)); // Vaults are trusted
            }

            best.deposit(withdrawn.sub(amount), sender);
            withdrawn = amount;
        }

        // `receiver` now has `withdrawn` tokens as balance
        if (receiver != address(this)) token.transfer(receiver, withdrawn);
    }

    function _migrate(address account) internal returns (uint256) {
        return _migrate(account, totalVaultBalance(account));
    }

    function _migrate(address account, uint256 amount) internal returns (uint256 migrated) {
        VaultAPI best = bestVault();

        uint256 alreadyDeposited = best.balanceOf(account).mul(best.pricePerShare()).div(10**uint256(best.decimals()));
        uint256 amountToMigrate = amount.sub(alreadyDeposited);

        uint256 depositLeft = best.depositLimit().sub(best.totalAssets());
        if (amountToMigrate > depositLeft) amountToMigrate = depositLeft;

        if (amountToMigrate > 0) {
            // NOTE: `false` = don't withdraw from `best`
            uint256 withdrawn = _withdraw(account, address(this), amountToMigrate, false);
            require(withdrawn == amountToMigrate);
            // NOTE: `false` = don't do `transferFrom` because it's already local
            migrated = _deposit(address(this), account, withdrawn, false);
            // NOTE: There's some precision loss here, but should be pretty bounded unless `decimals` is a really low number
            require(withdrawn - migrated <= 10);
        } // else: nothing to migrate! (not a failure)
    }
}
