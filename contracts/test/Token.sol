// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Token is ERC20 {
    mapping(address => bool) public _blocked;

    constructor(uint8 _decimals) public ERC20("yearn.finance test token", "TEST") {
        _setupDecimals(_decimals);
        _mint(msg.sender, 30000 * 10**uint256(_decimals));
    }

    function _setBlocked(address user, bool value) public virtual {
        _blocked[user] = value;
    }

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal virtual override(ERC20) {
        require(!_blocked[to], "Token transfer refused. Receiver is on blacklist");
        super._beforeTokenTransfer(from, to, amount);
    }
}

contract TokenNoReturn {
    using SafeMath for uint256;

    string public name;
    string public symbol;
    uint8 public decimals;

    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    mapping(address => bool) public _blocked;

    constructor(uint8 _decimals) public {
        name = "yearn.finance test token";
        symbol = "TEST";
        decimals = _decimals;
        balanceOf[msg.sender] = 30000 * 10**uint256(_decimals);
        totalSupply = 30000 * 10**uint256(_decimals);
    }

    function _setBlocked(address user, bool value) public virtual {
        _blocked[user] = value;
    }

    function transfer(address receiver, uint256 amount) external {
        require(!_blocked[receiver], "Token transfer refused. Receiver is on blacklist");
        balanceOf[msg.sender] = balanceOf[msg.sender].sub(amount);
        balanceOf[receiver] = balanceOf[receiver].add(amount);
        emit Transfer(msg.sender, receiver, amount);
    }

    function approve(address spender, uint256 amount) external {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
    }

    function transferFrom(
        address sender,
        address receiver,
        uint256 amount
    ) external {
        require(!_blocked[receiver], "Token transfer refused. Receiver is on blacklist");
        allowance[sender][msg.sender] = allowance[sender][msg.sender].sub(amount);
        balanceOf[sender] = balanceOf[sender].sub(amount);
        balanceOf[receiver] = balanceOf[receiver].add(amount);
        emit Transfer(sender, receiver, amount);
    }
}

contract TokenFalseReturn is Token {
    constructor(uint8 _decimals) public Token(_decimals) {}

    function transfer(address receiver, uint256 amount) public virtual override returns (bool) {
        return false;
    }

    function transferFrom(
        address sender,
        address receiver,
        uint256 amount
    ) public virtual override returns (bool) {
        return false;
    }
}
