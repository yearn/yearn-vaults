// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";

import {VaultAPI, BaseWrapper} from "./BaseWrapper.sol";

contract yToken is IERC20, BaseWrapper {
    using SafeMath for uint256;

    mapping(address => mapping(address => uint256)) public override allowance;

    constructor(address _token) public BaseWrapper(_token) {}

    function name() external view returns (string memory) {
        VaultAPI best = bestVault();
        return best.name();
    }

    function symbol() external view returns (string memory) {
        VaultAPI best = bestVault();
        return best.symbol();
    }

    function decimals() external view returns (uint256) {
        VaultAPI best = bestVault();
        return best.decimals();
    }

    function totalSupply() external override view returns (uint256 total) {
        return totalAssets();
    }

    function balanceOf(address account) external override view returns (uint256 balance) {
        return totalAssetsForAccount(account);
    }

    function _transfer(
        address sender,
        address receiver,
        uint256 amount
    ) internal {
        require(receiver != address(0), "ERC20: transfer to the zero address");
        require(amount == _withdraw(sender, receiver, amount, true)); // `true` means use `bestVault`
        emit Transfer(sender, receiver, amount);
    }

    function transfer(address receiver, uint256 amount) public virtual override returns (bool) {
        _transfer(msg.sender, receiver, amount);
        return true;
    }

    function _approve(
        address owner,
        address spender,
        uint256 amount
    ) internal {
        require(owner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");

        allowance[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }

    function approve(address spender, uint256 amount) public override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(
        address sender,
        address receiver,
        uint256 amount
    ) public virtual override returns (bool) {
        _transfer(sender, receiver, amount);
        _approve(sender, msg.sender, allowance[sender][msg.sender].sub(amount));
        return true;
    }

    function increaseAllowance(address spender, uint256 addedValue) public virtual returns (bool) {
        _approve(msg.sender, spender, allowance[msg.sender][spender].add(addedValue));
        return true;
    }

    function decreaseAllowance(address spender, uint256 subtractedValue) public virtual returns (bool) {
        _approve(msg.sender, spender, allowance[msg.sender][spender].sub(subtractedValue));
        return true;
    }

    function deposit(uint256 amount) external returns (uint256) {
        return _deposit(msg.sender, msg.sender, amount, true); // `true` = pull from sender
    }

    function withdraw(uint256 amount) external returns (uint256) {
        return _withdraw(msg.sender, msg.sender, amount, true); // `true` = withdraw from `best`
    }

    function permitAll(VaultAPI[] calldata vaults, bytes[] calldata signatures) external {
        require(vaults.length == signatures.length);
        for (uint256 i = 0; i < vaults.length; i++) {
            require(vaults[i].permit(msg.sender, address(this), uint256(-1), 0, signatures[i]));
        }
    }

    function migrate() external returns (uint256) {
        return _migrate(msg.sender);
    }
}
