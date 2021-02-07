// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";

import {RegistryAPI, VaultAPI} from "./BaseStrategy.sol";

abstract contract BaseWrapper {
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
}

contract MigrationWrapper is BaseWrapper {
    using SafeMath for uint256;

    constructor(address _token) public BaseWrapper(_token) {}

    function _migrate(address account) internal returns (uint256 migrated) {
        VaultAPI best = bestVault();
        uint256 deposit_limit = best.depositLimit().sub(best.totalAssets());
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            uint256 shares = vaults[id].balanceOf(account);

            if (vaults[id] == best) {
                break;
            }

            // NOTE: No need for allowance check if we are migrating the balance of this contract
            if (shares > 0 && (account == address(this) || vaults[id].allowance(account, address(this)) >= shares)) {
                // NOTE: There is a maximum withdrawal size from each vault (in shares)
                uint256 maxWithdrawal = vaults[id].maxAvailableShares();

                if (maxWithdrawal < shares) shares = maxWithdrawal;

                // NOTE: There is a maximum deposit size to the best vault (in tokens)
                uint256 maxDeposit = deposit_limit
                    .sub(migrated) // NOTE: Changes every iteration
                    .mul(vaults[id].pricePerShare()) // NOTE: Every Vault is different
                    .div(10**vaults[id].decimals());

                if (maxDeposit == 0) break; // avoid exhausting deposit limit
                if (maxDeposit < shares) shares = maxDeposit;

                // NOTE: No need for share transfer if we are migrating the balance of this contract
                if (account != address(this)) vaults[id].transferFrom(account, address(this), shares);
                migrated = migrated.add(vaults[id].withdraw(shares, address(this)));
            }
        }

        token.approve(address(best), migrated);
        best.deposit(migrated, account);
    }
}
