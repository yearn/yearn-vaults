// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.6.12;
pragma experimental ABIEncoderV2;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";

import {VaultAPI, MigrationWrapper} from "./BaseWrapper.sol";

contract yToken is IERC20, MigrationWrapper {
    using SafeMath for uint256;

    mapping(address => mapping(address => uint256)) public override allowance;

    constructor(address _token) public MigrationWrapper(_token) {}

    function migrate() external returns (uint256) {
        return _migrate(msg.sender);
    }

    function permitAll(VaultAPI[] calldata vaults, bytes[] calldata signatures) external {
        require(vaults.length == signatures.length);
        for (uint256 i = 0; i < vaults.length; i) {
            require(vaults[i].permit(msg.sender, address(this), uint256(-1), 0, signatures[i]));
        }
    }

    function deposit(uint256 amount) external returns (uint256) {
        VaultAPI vault = bestVault();

        token.transferFrom(msg.sender, address(this), amount);
        token.approve(address(vault), amount);

        return vault.deposit(amount, msg.sender);
    }

    function withdraw(uint256 amount) external returns (uint256) {
        _migrate(msg.sender);
        VaultAPI vault = bestVault();

        uint256 maxShares = amount.mul(vault.pricePerShare()).div(10**vault.decimals());
        return vault.withdraw(maxShares, msg.sender);
    }

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
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            total = total.add(vaults[id].totalSupply().mul(vaults[id].pricePerShare()).div(10**vaults[id].decimals()));
        }
    }

    function balanceOf(address account) external override view returns (uint256 balance) {
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            balance = balance.add(vaults[id].balanceOf(account).mul(vaults[id].pricePerShare()).div(10**vaults[id].decimals()));
        }
    }

    function _transfer(
        address sender,
        address receiver,
        uint256 amount
    ) internal {
        require(receiver != address(0), "ERC20: transfer to the zero address");

        _migrate(sender);

        VaultAPI best = bestVault();
        best.transferFrom(sender, receiver, amount);
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
}
