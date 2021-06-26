// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import {VaultAPI} from "../BaseStrategy.sol";

contract TestDeposit {
    using SafeERC20 for ERC20;

    address public  token;
    address public  targetVault;

    constructor(address _token, address _vault) public {
        token = _token;
        targetVault = _vault;
    }

    // Used to test an interaction from contract
    // Should fail via defend
    function deposit(uint256 amount) external {
        ERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        ERC20(token).safeApprove(targetVault, amount);
        VaultAPI(targetVault).deposit(amount);
    }
}
