// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelinV3/contracts/token/ERC20/ERC20.sol";

contract Token is ERC20 {
    constructor() public ERC20("yearn.finance test token", "TEST") {
        _mint(msg.sender, 30000 * 10**18);
    }
}
