// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.15;

interface IBaseFee {
    function basefee_global() external view returns (uint256);
}

/**
 * @dev Interprets the base fee from our base fee provider
 *  contract to determine if a harvest is permissable.
 *
 * Version 0.1.0
 */

contract BaseFeeOracle {
    address public baseFeeProvider; /// @notice Provider to read current block's base fee. This will vary based on network.
    uint256 public maxAcceptableBaseFee; /// @notice Max acceptable base fee for the operation

    address public governance; /// @notice Governance can grant and revoke access to the setter
    mapping(address => bool) public authorizedAddresses; /// @notice Addresses that can set the max acceptable base fee

    bool public manualBaseFeeBool; /// @notice Use this if our network hasn't implemented the base fee method yet

    constructor() {
        governance = msg.sender; // our deployer should be gov, they can set up the rest
        manualBaseFeeBool = true; // start as permissive
    }

    /// @notice Returns whether we should allow harvests based on current base fee.
    function isCurrentBaseFeeAcceptable() public view returns (bool) {
        if (baseFeeProvider == address(0)) {
            return manualBaseFeeBool;
        } else {
            uint256 baseFee = IBaseFee(baseFeeProvider).basefee_global();
            return baseFee <= maxAcceptableBaseFee;
        }
    }

    /// @notice Set the maximum base fee we want for our keepers to accept. Gwei is 1e9.
    function setMaxAcceptableBaseFee(uint256 _maxAcceptableBaseFee) external {
        _onlyAuthorized();
        maxAcceptableBaseFee = _maxAcceptableBaseFee;
    }

    /// @notice If we don't have a provider, then manually determine if true or not. Useful in testing as well.
    function setManualBaseFeeBool(bool _manualBaseFeeBool) external {
        _onlyAuthorized();
        manualBaseFeeBool = _manualBaseFeeBool;
    }

    /// @notice Set authorized addresses to set the acceptable base fee
    function setAuthorized(address _target) external {
        _onlyGovernance();
        authorizedAddresses[_target] = true;
    }

    /// @notice Update our governance address
    function setGovernance(address _target) external {
        _onlyGovernance();
        governance = _target;
    }

    /// @notice Set the address used to pull the current network base fee
    function setBaseFeeProvider(address _baseFeeProvider) external {
        _onlyGovernance();
        baseFeeProvider = _baseFeeProvider;
    }

    /// @notice Revoke an authorized address if they misbehave
    function revokeAuthorized(address _target) external {
        _onlyGovernance();
        authorizedAddresses[_target] = false;
    }

    function _onlyAuthorized() internal view {
        require(authorizedAddresses[msg.sender] == true || msg.sender == governance, "!authorized");
    }

    function _onlyGovernance() internal view {
        require(msg.sender == governance, "!governance");
    }
}
