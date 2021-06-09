// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import {ICustomHealthCheck} from "../interfaces/ICustomHealthCheck.sol";

contract TestHealthCheck is ICustomHealthCheck {
    bool pass;

    constructor() public {
        pass = true;
    }

    function togglePass() external {
        pass = !pass;
    }

    function check(
        uint256 profit,
        uint256 loss,
        address callerStrategy
    ) external view override returns (bool) {
        return pass;
    }
}
