// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy, StrategyParams, VaultAPI} from "../BaseStrategy.sol";

/*
 * This Strategy serves as both a mock Strategy for testing, and an example
 * for integrators on how to use BaseStrategy
 */

contract TestStrategy is BaseStrategy {
    bool public doReentrancy;

    constructor(address _vault) public BaseStrategy(_vault, "") {}

    function name() external override view returns (string memory) {
        return string(abi.encodePacked("TestStrategy ", apiVersion()));
    }

    // NOTE: This is a test-only function to simulate losses
    function _takeFunds(uint256 amount) public {
        want.transfer(msg.sender, amount);
    }

    // NOTE: This is a test-only function to enable reentrancy on withdraw
    function _toggleReentrancyExploit() public {
        doReentrancy = !doReentrancy;
    }

    function estimatedTotalAssets() public override view returns (uint256) {
        // For mock, this is just everything we have
        return want.balanceOf(address(this));
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // During testing, send this contract some tokens to simulate "Rewards"
        uint256 totalAssets = want.balanceOf(address(this));
        uint256 totalDebt = vault.strategies(address(this)).totalDebt;
        if (totalAssets > _debtOutstanding) {
            _debtPayment = _debtOutstanding;
            totalAssets = totalAssets.sub(_debtOutstanding);
        } else {
            _debtPayment = totalAssets;
            totalAssets = 0;
        }
        totalDebt = totalDebt.sub(_debtPayment);

        if (totalAssets > totalDebt) {
            _profit = totalAssets.sub(totalDebt);
        } else {
            _loss = totalDebt.sub(totalAssets);
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        // Whatever we have "free", consider it "invested" now
    }

    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _liquidatedAmount, uint256 _loss) {
        if (doReentrancy) {
            // simulate a malicious protocol or reentrancy situation triggered by strategy withdraw interactions
            uint256 stratBalance = VaultAPI(address(vault)).balanceOf(address(this));
            VaultAPI(address(vault)).withdraw(stratBalance, address(this));
        }

        uint256 totalDebt = vault.strategies(address(this)).totalDebt;
        uint256 totalAssets = want.balanceOf(address(this));
        if (_amountNeeded > totalAssets) {
            _liquidatedAmount = totalAssets;
            _loss = _amountNeeded.sub(totalAssets);
        } else {
            // NOTE: Just in case something was stolen from this contract
            if (totalDebt > totalAssets) {
                _loss = totalDebt.sub(totalAssets);
                if (_loss > _amountNeeded) _loss = _amountNeeded;
            }
            _liquidatedAmount = _amountNeeded;
        }
    }

    function prepareMigration(address _newStrategy) internal override {
        // Nothing needed here because no additional tokens/tokenized positions for mock
    }

    function protectedTokens() internal override view returns (address[] memory) {
        return new address[](0); // No additional tokens/tokenized positions for mock
    }
}
