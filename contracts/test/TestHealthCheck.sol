// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import {ICustomHealthCheck} from "../interfaces/ICustomHealthCheck.sol";

contract TestHealthCheck is ICustomHealthCheck {
    bool pass;

    constructor() {
        pass = true;
    }

    function togglePass() external {
        pass = !pass;
    }

    function check(
        address callerStrategy,
        uint256 profit,
        uint256 loss,
        uint256 debtPayment,
        uint256 debtOutstanding
    ) external view override returns (bool) {
        return pass;
    }
}
