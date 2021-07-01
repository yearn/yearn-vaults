// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import {VaultAPI} from "./BaseStrategy.sol";

interface RegistryAPI {
    function governance() external view returns (address);

    function latestVault(address token) external view returns (address);

    function numVaults(address token) external view returns (uint256);

    function vaults(address token, uint256 deploymentId) external view returns (address);
}

contract Router {
    RegistryAPI public registry;
    uint256 constant DEPOSIT_EVERYTHING = type(uint256).max;
    uint256 constant UNLIMITED_APPROVAL = type(uint256).max;

    constructor(address _registry) public {
        // Recommended to use `v2.registry.ychad.eth`
        registry = RegistryAPI(_registry);
    }

    function deposit(
        IERC20 _token, // Token to deposit
        uint256 amount // if `MAX_UINT256`, just deposit everything
    ) public {
        VaultAPI vault = latestVault(address(_token));
        assert(address(vault) != 0x0000000000000000000000000000000000000000);
        if (amount == DEPOSIT_EVERYTHING) {
            amount = _token.balanceOf(msg.sender);
        }
        SafeERC20.safeTransferFrom(_token, msg.sender, address(this), amount);

        if (_token.allowance(address(this), address(vault)) < amount) {
            SafeERC20.safeApprove(_token, address(vault), 0); // Avoid issues with some tokens requiring 0
            SafeERC20.safeApprove(_token, address(vault), UNLIMITED_APPROVAL); // Vaults are trusted
        }

        vault.deposit(amount, msg.sender);
    }

    /* @notice
     *  Used to get the most recent vault for the token using the registry.
     * @return An instance of a VaultAPI
     */
    function latestVault(address _token) public view virtual returns (VaultAPI) {
        return VaultAPI(registry.latestVault(_token));
    }
}
