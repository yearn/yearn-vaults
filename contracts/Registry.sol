// SPDX-License-Identifier: MIT
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/token/ERC20/ERC20.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/utils/EnumerableSet.sol";

import {VaultAPI} from "./BaseStrategy.sol";

struct VaultData {
    address vaultAddress;
    string vaultName;
    string vaultSymbol;
    string vaultApiVersion;
    address tokenAddress;
    string tokenName;
    string tokenSymbol;
    uint256 tokenDecimals; // NOTE: Vault.decimals() == Token.decimals()
}

contract Registry {
    using Address for address;
    using SafeMath for uint256;
    using EnumerableSet for EnumerableSet.AddressSet;

    address public governance;
    address pendingGovernance;

    EnumerableSet.AddressSet private vaults;

    constructor(address _governance) public {
        require(_governance != address(0), "Missing Governance");
        governance = _governance;
    }

    // Governance setters
    function setGovernance(address _governance) external onlyGovernance {
        pendingGovernance = _governance;
    }

    function acceptGovernance() external {
        require(msg.sender == pendingGovernance, "!pendingGovernance");
        governance = msg.sender;
    }

    modifier onlyGovernance {
        require(msg.sender == governance, "!governance");
        _;
    }

    // Vault set actions
    function addVault(address _vault) public onlyGovernance {
        require(_vault.isContract(), "Vault is not a contract");
        // Checks if vault is already on the array
        require(!vaults.contains(_vault), "Vault already exists");
        // Adds unique _vault to vaults array
        vaults.add(_vault);
    }

    function removeVault(address _vault) public onlyGovernance {
        // Checks if vault is already on the array
        require(vaults.contains(_vault), "Vault not in set");
        // Remove _vault to vaults array
        vaults.remove(_vault);
    }

    function getVaultData(address _vault) internal view returns (VaultData memory) {
        address token = VaultAPI(_vault).token();
        return
            VaultData({
                vaultAddress: _vault,
                vaultName: VaultAPI(_vault).name(),
                vaultSymbol: VaultAPI(_vault).symbol(),
                vaultApiVersion: VaultAPI(_vault).apiVersion(),
                tokenAddress: token,
                tokenName: ERC20(token).name(),
                tokenSymbol: ERC20(token).symbol(),
                tokenDecimals: ERC20(token).decimals()
            });
    }

    // Vaults getters
    function getVault(uint256 _index) external view returns (VaultData memory) {
        return getVaultData(vaults.at(_index));
    }

    function getVault(address _vault) external view returns (VaultData memory) {
        return getVaultData(_vault);
    }

    function getVaultsLength() external view returns (uint256) {
        return vaults.length();
    }

    function getVaults() external view returns (VaultData[] memory) {
        VaultData[] memory vaultsArray = new VaultData[](vaults.length());
        for (uint256 i = 0; i < vaults.length(); i++) {
            vaultsArray[i] = getVaultData(vaults.at(i));
        }
        return vaultsArray;
    }
}
