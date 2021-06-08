// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import {ICustomHealthCheck} from "../interfaces/ICustomHealthCheck.sol";

contract TestHealthCheck is ICustomHealthCheck {
    function check(
        uint256 profit,
        uint256 loss,
        uint256 callerStrategy
    ) external view override returns (bool) {
        return true;
    }
}
