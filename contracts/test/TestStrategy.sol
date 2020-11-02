// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy, StrategyParams} from "../BaseStrategy.sol";

/*
 * This Strategy serves as both a mock Strategy for testing, and an example
 * for integrators on how to use BaseStrategy
 */

contract TestStrategy is BaseStrategy {
    constructor(address _vault) public BaseStrategy(_vault) {}

    function name() external override pure returns (string memory) {
        return "TestStrategy";
    }

    // When exiting the position, wait this many times to give everything back
    uint256 countdownTimer = 3;

    // NOTE: This is a test-only function
    function _takeFunds(uint256 amount) public {
        want.transfer(msg.sender, amount);
    }

    function estimatedTotalAssets() public override view returns (uint256) {
        // For mock, this is just everything we have
        return want.balanceOf(address(this));
    }

    function prepareReturn(uint256 _debtOutstanding) internal override returns (uint256 _profit) {
        // During testing, send this contract some tokens to simulate "Rewards"
        uint256 reserve = getReserve();
        uint256 total = want.balanceOf(address(this));
        if (total > reserve.add(_debtOutstanding)) _profit = total.sub(reserve).sub(_debtOutstanding);
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        // Whatever we have "free", consider it "invested" now
        uint256 total = want.balanceOf(address(this));
        if (total > _debtOutstanding) {
            setReserve(total.sub(_debtOutstanding));
        } else {
            setReserve(0);
        }
    }

    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _amountFreed) {
        uint256 reserve = getReserve();
        if (_amountNeeded >= reserve) {
            // Give back the entire reserves
            _amountFreed = reserve;
        } else {
            // Give back a portion of the reserves
            _amountFreed = _amountNeeded;
        }
        setReserve(reserve.sub(_amountFreed));
    }

    function exitPosition() internal override {
        // Dump 1/N of original position each time this is called
        setReserve(want.balanceOf(address(this)).mul(countdownTimer.sub(1)).div(countdownTimer));
        countdownTimer = countdownTimer.sub(1); // NOTE: This should never be called after it hits 0
    }

    function prepareMigration(address _newStrategy) internal override {
        // Nothing needed here because no additional tokens/tokenized positions for mock
    }

    function protectedTokens() internal override view returns (address[] memory) {
        return new address[](0); // No additional tokens/tokenized positions for mock
    }
}
