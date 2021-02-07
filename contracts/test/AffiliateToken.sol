// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

import {VaultAPI, MigrationWrapper} from "../BaseWrapper.sol";

contract AffiliateToken is ERC20, MigrationWrapper {
    address public affliate;

    modifier onlyAffliate() {
        require(msg.sender == affliate);
        _;
    }

    constructor(
        address _token,
        string memory name,
        string memory symbol
    ) public MigrationWrapper(_token) ERC20(name, symbol) {
        _setupDecimals(uint8(token.decimals()));
    }

    function totalAssets() public returns (uint256 totalTokenBalance) {
        VaultAPI[] memory vaults = allVaults();

        for (uint256 id = 0; id < vaults.length; id++) {
            uint256 tokensInVault = vaults[id].balanceOf(address(this)).mul(vaults[id].pricePerShare()).div(10**uint256(vaults[id].decimals()));

            totalTokenBalance = totalTokenBalance.add(tokensInVault);
        }
    }

    function _shareValue(uint256 numShares) internal returns (uint256) {
        uint256 totalTokenBalance = totalAssets();

        if (totalTokenBalance > 0) {
            return totalTokenBalance.mul(numShares).div(totalSupply());
        } else {
            return 0;
        }
    }

    function pricePerShare() external returns (uint256) {
        return _shareValue(10**token.decimals());
    }

    function deposit(uint256 amount) external returns (uint256 shares) {
        VaultAPI vault = bestVault();

        token.transferFrom(msg.sender, address(this), amount);
        token.approve(address(vault), amount);

        shares = vault.deposit(amount);
        _mint(msg.sender, amount);
    }

    function withdraw(uint256 shares) external returns (uint256) {
        _burn(msg.sender, shares);
        VaultAPI vault = bestVault();
        uint256 amount = _shareValue(shares);
        uint256 sharesFromLatest = amount.mul(vault.pricePerShare()).div(10**uint256(vault.decimals()));
        return vault.withdraw(sharesFromLatest, msg.sender);
    }

    function migrate() external onlyAffliate returns (uint256) {
        _migrate(address(this));
    }
}
