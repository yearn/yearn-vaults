// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

interface IBaseFee {
    function basefee_global() external view returns (uint256);
}

contract BaseFeeOracle {
    // Provider to read current block's base fee. this will change if using a network other than etherum.
    IBaseFee internal constant baseFeeProvider = IBaseFee(0xf8d0Ec04e94296773cE20eFbeeA82e76220cD549);

    // Max acceptable base fee for the operation
    uint256 public maxAcceptableBaseFee;

    // Boolean to determine if we are in testing mode or not, only controllable by gov
    bool public useTesting;

    // Governance can grant and revoke access to the setter
    address public governance;

    // Addresses that can set the max acceptable base fee
    mapping(address => bool) public authorizedAddresses;

    constructor() public {
        governance = msg.sender; // our deployer should be gov, they can set up the rest
    }

    ///@notice Returns whether we should allow harvests based on current base fee.
    function isCurrentBaseFeeAcceptable() public view returns (bool) {
        uint256 baseFee;

        if (useTesting) {
            // when testing on development network, we need to be able to hardcode this
            // without fear of reverts.
            baseFee = 1000 gwei;
        } else {
            try baseFeeProvider.basefee_global() returns (uint256 currentBaseFee) {
                baseFee = currentBaseFee;
            } catch {
                // Useful for testing until ganache supports london fork
                // Hard-code current base fee to 1000 gwei
                // This should also help keepers that run in a fork without
                // baseFee() to avoid reverting and potentially abandoning the job
                baseFee = 1000 gwei;
            }
        }

        return baseFee <= maxAcceptableBaseFee;
    }

    function setMaxAcceptableBaseFee(uint256 _maxAcceptableBaseFee) external {
        _onlyAuthorized();
        maxAcceptableBaseFee = _maxAcceptableBaseFee;
    }

    function setAuthorized(address _target) external {
        _onlyGovernance();
        authorizedAddresses[_target] = true;
    }

    function setGovernance(address _target) external {
        _onlyGovernance();
        governance = _target;
    }

    ///@notice This should never be used in production, only in testing
    function setUseTesting(bool _useTesting) external {
        _onlyGovernance();
        useTesting = _useTesting;
    }

    function revokeAuthorized(address _target) external {
        _onlyGovernance();
        authorizedAddresses[_target] = false;
    }

    function _onlyAuthorized() internal view {
        require(authorizedAddresses[msg.sender] == true, "!authorized");
    }

    function _onlyGovernance() internal view {
        require(msg.sender == governance, "!governance");
    }
}
