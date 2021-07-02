// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import {VaultAPI} from "../BaseStrategy.sol";

contract TestFlashLoan {
    using SafeERC20 for ERC20;

    address public  token;
    address public  targetVault;

    constructor(address _token, address _vault) public {
        token = _token;
        targetVault = _vault;
    }

    // Deposits and sends back, used to test against deposit and withdraw on the same block
    // Should fail with lockForBlock
    function flashLoan(uint256 amount) external {
        ERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        ERC20(token).safeApprove(targetVault, amount);
        uint256 shares = VaultAPI(targetVault).deposit(amount);
        VaultAPI(targetVault).withdraw(shares);
        ERC20(token).safeTransfer(msg.sender, shares);
    }
}
