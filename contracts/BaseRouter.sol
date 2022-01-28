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

    function numVaults(address token) external view returns (uint256);

    function vaults(address token, uint256 deploymentId) external view returns (address);
}

/**
 * @title Yearn Base Router
 * @author yearn.finance
 * @notice
 *  BaseRouter implements all of the required functionality to interoperate
 *  closely with the Vault contract. This contract should be inherited and the
 *  abstract methods implemented to adapt the Router.
 *  A good starting point to build a router is https://github.com/yearn/brownie-router-mix
 *
 */
abstract contract BaseRouter {
    using Math for uint256;
    using SafeMath for uint256;

    // Reduce number of external calls (SLOADs stay the same)
    mapping(address => VaultAPI[]) private _cachedVaults;

    RegistryAPI public registry;

    // ERC20 Unlimited Approvals (short-circuits VaultAPI.transferFrom)
    uint256 constant UNLIMITED_APPROVAL = type(uint256).max;
    // Sentinal values used to save gas on deposit/withdraw/migrate
    // NOTE: DEPOSIT_EVERYTHING == WITHDRAW_EVERYTHING == MIGRATE_EVERYTHING
    uint256 constant DEPOSIT_EVERYTHING = type(uint256).max;
    uint256 constant WITHDRAW_EVERYTHING = type(uint256).max;

    constructor(address _registry) public {
        // Recommended to use `v2.registry.ychad.eth`
        registry = RegistryAPI(_registry);
    }

    /**
     * @notice
     *  Used to update the yearn registry.
     * @param _registry The new _registry address.
     */
    function setRegistry(address _registry) external {
        require(msg.sender == registry.governance());
        // In case you want to override the registry instead of re-deploying
        registry = RegistryAPI(_registry);
        // Make sure there's no change in governance
        // NOTE: Also avoid bricking the router from setting a bad registry
        require(msg.sender == registry.governance());
    }

    /**
     * @notice
     *  Used to get the most recent vault for the token using the registry.
     * @return An instance of a VaultAPI
     */
    function bestVault(address token) public view virtual returns (VaultAPI) {
        return VaultAPI(registry.latestVault(token));
    }

    /**
     * @notice
     *  Used to get all vaults from the registery for the token
     * @return An array containing instances of VaultAPI
     */
    function allVaults(address token) public view virtual returns (VaultAPI[] memory) {
        uint256 cache_length = _cachedVaults[token].length;
        uint256 num_vaults = registry.numVaults(token);

        // Use cached
        if (cache_length == num_vaults) {
            return _cachedVaults[token];
        }

        VaultAPI[] memory vaults = new VaultAPI[](num_vaults);

        for (uint256 vault_id = 0; vault_id < cache_length; vault_id++) {
            vaults[vault_id] = _cachedVaults[token][vault_id];
        }

        for (uint256 vault_id = cache_length; vault_id < num_vaults; vault_id++) {
            vaults[vault_id] = VaultAPI(registry.vaults(token, vault_id));
        }

        return vaults;
    }

    function _updateVaultCache(address token, VaultAPI[] memory vaults) internal {
        // NOTE: even though `registry` is update-able by Yearn, the intended behavior
        //       is that any future upgrades to the registry will replay the version
        //       history so that this cached value does not get out of date.
        if (vaults.length > _cachedVaults[token].length) {
            _cachedVaults[token] = vaults;
        }
    }

    /**
     * @notice
     *  Used to get the balance of an account accross all the vaults for a token.
     *  @dev will be used to get the router balance using totalVaultBalance(address(this)).
     *  @param account The address of the account.
     *  @return balance of token for the account accross all the vaults.
     */
    function totalVaultBalance(address token, address account) public view returns (uint256 balance) {
        VaultAPI[] memory vaults = allVaults(token);

        for (uint256 id = 0; id < vaults.length; id++) {
            balance = balance.add(vaults[id].balanceOf(account).mul(vaults[id].pricePerShare()).div(10**uint256(vaults[id].decimals())));
        }
    }

    /**
     * @notice
     *  Used to get the TVL on the underlying vaults.
     *  @return assets the sum of all the assets managed by the underlying vaults.
     */
    function totalAssets(address token) public view returns (uint256 assets) {
        VaultAPI[] memory vaults = allVaults(token);

        for (uint256 id = 0; id < vaults.length; id++) {
            assets = assets.add(vaults[id].totalAssets());
        }
    }

    function _deposit(
        IERC20 token,
        address depositor,
        address receiver,
        uint256 amount, // if `MAX_UINT256`, just deposit everything
        bool pullFunds // If true, funds need to be pulled from `depositor` via `transferFrom`
    ) internal returns (uint256 deposited) {
        VaultAPI _bestVault = bestVault(address(token));

        if (pullFunds) {
            if (amount == DEPOSIT_EVERYTHING) {
                amount = token.balanceOf(depositor);
            }
            SafeERC20.safeTransferFrom(token, depositor, address(this), amount);
        }

        if (token.allowance(address(this), address(_bestVault)) < amount) {
            SafeERC20.safeApprove(token, address(_bestVault), 0); // Avoid issues with some tokens requiring 0
            SafeERC20.safeApprove(token, address(_bestVault), UNLIMITED_APPROVAL); // Vaults are trusted
        }

        // Depositing returns number of shares deposited
        // NOTE: Shortcut here is assuming the number of tokens deposited is equal to the
        //       number of shares credited, which helps avoid an occasional multiplication
        //       overflow if trying to adjust the number of shares by the share price.
        uint256 beforeBal = token.balanceOf(address(this));
        if (receiver != address(this)) {
            _bestVault.deposit(amount, receiver);
        } else if (amount != DEPOSIT_EVERYTHING) {
            _bestVault.deposit(amount);
        } else {
            _bestVault.deposit();
        }

        uint256 afterBal = token.balanceOf(address(this));
        deposited = beforeBal.sub(afterBal);
        // `receiver` now has shares of `_bestVault` as balance, converted to `token` here
        // Issue a refund if not everything was deposited
        if (depositor != address(this) && afterBal > 0) SafeERC20.safeTransfer(token, depositor, afterBal);
    }

    function _withdraw(
        IERC20 token,
        address sender,
        address receiver,
        uint256 amount, // if `MAX_UINT256`, just withdraw everything
        bool withdrawFromBest // If true, also withdraw from `_bestVault`
    ) internal returns (uint256 withdrawn) {
        VaultAPI _bestVault = bestVault(address(token));

        VaultAPI[] memory vaults = allVaults(address(token));
        _updateVaultCache(address(token), vaults);

        // NOTE: This loop will attempt to withdraw from each Vault in `allVaults` that `sender`
        //       is deposited in, up to `amount` tokens. The withdraw action can be expensive,
        //       so it if there is a denial of service issue in withdrawing, the downstream usage
        //       of this router contract must give an alternative method of withdrawing using
        //       this function so that `amount` is less than the full amount requested to withdraw
        //       (e.g. "piece-wise withdrawals"), leading to less loop iterations such that the
        //       DoS issue is mitigated (at a tradeoff of requiring more txns from the end user).
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
                // Intermediate step to move shares to this contract before withdrawing
                // NOTE: No need for share transfer if this contract is `sender`

                if (amount != WITHDRAW_EVERYTHING) {
                    // Compute amount to withdraw fully to satisfy the request
                    uint256 estimatedShares = amount
                    .sub(withdrawn) // NOTE: Changes every iteration
                    .mul(10**uint256(vaults[id].decimals()))
                    .div(vaults[id].pricePerShare()); // NOTE: Every Vault is different

                    // Limit amount to withdraw to the maximum made available to this contract
                    // NOTE: Avoid corner case where `estimatedShares` isn't precise enough
                    // NOTE: If `0 < estimatedShares < 1` but `availableShares > 1`, this will withdraw more than necessary
                    if (estimatedShares > 0 && estimatedShares < availableShares) {
                        if (sender != address(this)) vaults[id].transferFrom(sender, address(this), estimatedShares);
                        withdrawn = withdrawn.add(vaults[id].withdraw(estimatedShares));
                    } else {
                        if (sender != address(this)) vaults[id].transferFrom(sender, address(this), availableShares);
                        withdrawn = withdrawn.add(vaults[id].withdraw(availableShares));
                    }
                } else {
                    if (sender != address(this)) vaults[id].transferFrom(sender, address(this), availableShares);
                    withdrawn = withdrawn.add(vaults[id].withdraw());
                }

                // Check if we have fully satisfied the request
                // NOTE: use `amount = WITHDRAW_EVERYTHING` for withdrawing everything
                if (amount <= withdrawn) break; // withdrawn as much as we needed
            }
        }

        // If we have extra, deposit back into `_bestVault` for `sender`
        // NOTE: Invariant is `withdrawn <= amount`
        if (withdrawn > amount && withdrawn.sub(amount) > _bestVault.pricePerShare().div(10**_bestVault.decimals())) {
            // Don't forget to approve the deposit
            if (token.allowance(address(this), address(_bestVault)) < withdrawn.sub(amount)) {
                SafeERC20.safeApprove(token, address(_bestVault), UNLIMITED_APPROVAL); // Vaults are trusted
            }

            _bestVault.deposit(withdrawn.sub(amount), sender);
            withdrawn = amount;
        }

        // `receiver` now has `withdrawn` tokens as balance
        if (receiver != address(this)) SafeERC20.safeTransfer(token, receiver, withdrawn);
    }
}
