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
    /// @notice Provider to read current block's base fee. This will vary based on network.
    address public baseFeeProvider;
    
    /// @notice Max acceptable base fee for the operation
    uint256 public maxAcceptableBaseFee;

    /// @notice Governance can grant and revoke access to the setter
    address public governance;
    
    /// @notice New address must be set by current gov and then accept to transfer power.
    address public pendingGovernance;
    
    /// @notice Addresses that can set the max acceptable base fee
    mapping(address => bool) public authorizedAddresses;
    
    /// @notice Use this if our network hasn't implemented the base fee method yet
    bool public manualBaseFeeBool;

    constructor() {
        governance = msg.sender; // our deployer should be gov, they can set up the rest
        manualBaseFeeBool = true; // start as permissive
    }

    // events for subgraph
    event NewGovernance(address indexed governance);

    event NewProvider(address indexed provider);

    event UpdatedMaxBaseFee(uint256 baseFee);

    event UpdatedManualBaseFee(bool manualFee);

    event UpdatedAuthorization(address indexed target, bool authorized);

    /// @notice Returns whether we should allow harvests based on current base fee.
    function isCurrentBaseFeeAcceptable() public view returns (bool) {
        if (baseFeeProvider == address(0)) {
            return manualBaseFeeBool;
        } else {
            uint256 baseFee = IBaseFee(baseFeeProvider).basefee_global();
            return baseFee <= maxAcceptableBaseFee;
        }
    }

    /**
     * @notice Set the maximum base fee we want for our keepers to accept.
     *  Gwei is 1e9.
     * @dev Throws if the caller is not authorized or gov.
     * @param _maxAcceptableBaseFee The acceptable maximum price to pay in wei.
     */
    function setMaxAcceptableBaseFee(uint256 _maxAcceptableBaseFee) external {
        _onlyAuthorized();
        maxAcceptableBaseFee = _maxAcceptableBaseFee;
        emit UpdatedMaxBaseFee(_maxAcceptableBaseFee);
    }

    /**
     * @notice If we don't have a provider, then manually determine if true or not.
     *  Useful in testing as well.
     * @dev Throws if the caller is not authorized or gov.
     * @param _manualBaseFeeBool Boolean to allow/block harvests if we don't
     *  have a provider set up.
     */
    function setManualBaseFeeBool(bool _manualBaseFeeBool) external {
        _onlyAuthorized();
        manualBaseFeeBool = _manualBaseFeeBool;
        emit UpdatedManualBaseFee(_manualBaseFeeBool);
    }

    /**
     * @notice Controls whether a non-gov address can adjust certain params.
     * @dev Throws if the caller is not current governance.
     * @param _target The address to add/remove authorization for.
     * @param _value Boolean to grant or revoke access.
     */
    function setAuthorized(address _target, bool _value) external {
        _onlyGovernance();
        authorizedAddresses[_target] = _value;
        emit UpdatedAuthorization(_target, _value);
    }

    /**
     * @notice Starts the 1st phase of the governance transfer.
     * @dev Throws if the caller is not current governance.
     * @param _governance The next governance address
     */
    function setPendingGovernance(address _governance) external {
        _onlyGovernance();
        pendingGovernance = _governance;
    }

    /**
     * @notice Completes the 2nd phase of the governance transfer.
     * @dev Throws if the caller is not the pending caller.
     *  Emits a `NewGovernance` event.
     */
    function acceptGovernance() external {
        require(msg.sender == pendingGovernance, "!authorized");
        governance = msg.sender;
        emit NewGovernance(msg.sender);
    }

    /**
     * @notice Sets the address used to pull the current network base fee.
     * @dev Throws if the caller is not current governance.
     * @param _baseFeeProvider The network's baseFeeProvider address
     */
    function setBaseFeeProvider(address _baseFeeProvider) external {
        _onlyGovernance();
        baseFeeProvider = _baseFeeProvider;
        emit NewProvider(_baseFeeProvider);
    }

    function _onlyAuthorized() internal view {
        require(authorizedAddresses[msg.sender] == true || msg.sender == governance, "!authorized");
    }

    function _onlyGovernance() internal view {
        require(msg.sender == governance, "!governance");
    }
}
