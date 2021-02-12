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

    // v2.registry.ychad.eth
    RegistryAPI constant registry = RegistryAPI(0xE15461B18EE31b7379019Dc523231C57d1Cbc18c);

    constructor(address _token) public {
        token = ERC20(_token);
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
        if (vaults.length > 0) {
            _cachedVaults = vaults;
        }
    }

    function totalBalance(address account) public view returns (uint256 balance) {
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            balance = balance.add(vaults[id].balanceOf(account).mul(vaults[id].pricePerShare()).div(10**vaults[id].decimals()));
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

        if (pullFunds) token.transferFrom(depositor, address(this), amount);

        if (token.allowance(address(this), address(best)) < uint256(-1)) {
            token.approve(address(best), uint256(-1)); // Vaults are trusted
        }

        // `receiver` now has shares of `best` (worth `amount` tokens) as balance
        return
            best
                .deposit(amount, reciever)
                .mul(10**3) // Add 3 extra decimals of precision
                .mul(best.pricePerShare()) // Adjust by price of best
                .div(10**best.decimals())
                .div(10**3); // Add 3 extra decimals of precision
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

            uint256 shares = vaults[id].balanceOf(sender);

            // NOTE: No need for allowance check if we are withdrawing the balance from this contract
            if (shares > 0 && (sender == address(this) || vaults[id].allowance(sender, address(this)) >= shares)) {
                // NOTE: There is a maximum withdrawal size from each vault (in shares)
                uint256 maxWithdrawal = vaults[id].maxAvailableShares();

                if (maxWithdrawal < shares) shares = maxWithdrawal;

                // NOTE: use `uint256(-1)` for withdrawing everything
                uint256 withdrawalLeft = amount
                    .sub(withdrawn) // NOTE: Changes every iteration
                    .mul(vaults[id].pricePerShare()) // NOTE: Every Vault is different
                    .div(10**vaults[id].decimals());

                if (withdrawalLeft == 0) break; // withdrawn as much as we needed
                if (withdrawalLeft < shares) shares = withdrawalLeft;

                // NOTE: No need for share transfer if we are migrating the balance of this contract
                if (sender != address(this)) vaults[id].transferFrom(sender, address(this), shares);
                withdrawn = withdrawn.add(vaults[id].withdraw(shares, receiver));
            }
        }
        // `receiver` now has `withdrawn` tokens as balance
    }

    function _migrate(address account) internal returns (uint256 migrated) {
        VaultAPI best = bestVault();

        uint256 alreadyDeposited = best.balanceOf(account).mul(best.pricePerShare()).div(10**best.decimals());
        uint256 amountToMigrate = totalBalance(account).sub(alreadyDeposited);

        uint256 depositLeft = best.depositLimit().sub(best.totalAssets());
        if (amountToMigrate > depositLeft) amountToMigrate = depositLeft;

        if (amountToMigrate > 0) {
            migrated = _withdraw(account, address(this), amountToMigrate, false); // `false` = don't withdraw from `best`
            require(migrated == amountToMigrate);
            require(migrated == _deposit(address(this), account, migrated, false)); // `false` = don't do `transferFrom` because it's already local
        } // else: nothing to migrate! (not a failure)
    }
}
