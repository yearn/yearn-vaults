// SPDX-License-Identifier: MIT
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelinV3/contracts/math/SafeMath.sol";
import "@openzeppelinV3/contracts/token/ERC20/ERC20.sol";
import "@openzeppelinV3/contracts/utils/Address.sol";
import "@openzeppelinV3/contracts/utils/EnumerableSet.sol";

import {VaultAPI} from "./BaseStrategy.sol";

enum VaultStatus {Invalid, Experimental, Endorsed, Deprecated}

struct VaultData {
    VaultStatus status;
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
    mapping(address => address) public latestVaultForToken;

    // Keep track of status
    EnumerableSet.AddressSet private experimentalVaults;
    EnumerableSet.AddressSet private endorsedVaults;
    EnumerableSet.AddressSet private deprecatedVaults;

    event VaultUpgrade(address indexed token, address indexed oldVault, address newVault);

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
    function addVault(address _vault, bool experimental) public onlyGovernance {
        require(_vault.isContract(), "Vault is not a contract");
        // Checks if vault is already on the array
        require(!vaults.contains(_vault), "Vault already exists");
        // Adds unique _vault to vaults array
        vaults.add(_vault);

        if (experimental) {
            experimentalVaults.add(_vault);
        } else {
            endorsedVaults.add(_vault);
        }

        // Keep track of latest Vault (newest is considered best)
        // NOTE: A vault should only be added to the registry when it's considered
        //       "production" ready, signaling it as the one people should upgrade to
        address token = VaultAPI(_vault).token();
        address oldVault = latestVaultForToken[token];
        latestVaultForToken[token] = _vault;
        emit VaultUpgrade(token, oldVault, _vault);
    }

    function endorseVault(address _vault) public onlyGovernance {
        require(experimentalVaults.contains(_vault), "!experimental");
        experimentalVaults.remove(_vault);
        endorsedVaults.add(_vault);
    }

    function removeVault(address _vault) public onlyGovernance {
        // Checks if vault is already on the array
        require(vaults.contains(_vault), "Vault not in set");
        // Remove _vault to vaults array
        vaults.remove(_vault);

        if (experimentalVaults.contains(_vault)) {
            experimentalVaults.remove(_vault);
        } else {
            endorsedVaults.remove(_vault);
        }
        deprecatedVaults.add(_vault);

        // Keep track of latest Vault (see if completely removed)
        // NOTE: If this removal action is trigger resetting to 0x0, this token is
        //       now considered "unsupported" by Yearn
        address token = VaultAPI(_vault).token();
        address currentVault = latestVaultForToken[token];
        if (currentVault == _vault) {
            latestVaultForToken[token] = address(0x0);
            emit VaultUpgrade(token, _vault, address(0x0));
        }
    }

    function getVaultData(address _vault) internal view returns (VaultData memory) {
        VaultStatus status = VaultStatus.Invalid;
        if (experimentalVaults.contains(_vault)) status = VaultStatus.Experimental;
        if (endorsedVaults.contains(_vault)) status = VaultStatus.Endorsed;
        if (deprecatedVaults.contains(_vault)) status = VaultStatus.Deprecated;

        address token = VaultAPI(_vault).token();
        return
            VaultData({
                status: status,
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

    function getActiveVaults() external view returns (VaultData[] memory) {
        VaultData[] memory vaultsArray = new VaultData[](vaults.length());
        for (uint256 i = 0; i < vaults.length(); i++) {
            vaultsArray[i] = getVaultData(vaults.at(i));
        }
        return vaultsArray;
    }

    function getExperimentalVaults() external view returns (VaultData[] memory) {
        VaultData[] memory vaultsArray = new VaultData[](vaults.length());
        for (uint256 i = 0; i < experimentalVaults.length(); i++) {
            vaultsArray[i] = getVaultData(experimentalVaults.at(i));
        }
        return vaultsArray;
    }

    function getEndorsedVaults() external view returns (VaultData[] memory) {
        VaultData[] memory vaultsArray = new VaultData[](vaults.length());
        for (uint256 i = 0; i < endorsedVaults.length(); i++) {
            vaultsArray[i] = getVaultData(endorsedVaults.at(i));
        }
        return vaultsArray;
    }

    function getDeprecatedVaults() external view returns (VaultData[] memory) {
        VaultData[] memory vaultsArray = new VaultData[](vaults.length());
        for (uint256 i = 0; i < deprecatedVaults.length(); i++) {
            vaultsArray[i] = getVaultData(deprecatedVaults.at(i));
        }
        return vaultsArray;
    }
}
