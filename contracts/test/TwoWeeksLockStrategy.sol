// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy, StrategyParams} from "../BaseStrategy.sol";

/*
 * This Strategy a test strategy which locks funds for 2 weeks and returns
 * a 10% (to make math easy).
 * It will not use tend and it will harvest when the lock up period is done
 */

contract TwoWeeksLockStrategy is BaseStrategy {
    constructor(address _vault, address _governance) public BaseStrategy(_vault) {}

    // Time the strategy will have funds locked
    uint256 public lockupPeriod = 2 weeks;
    uint256 public timeOfInvestment = uint256(-1); // Using -1 to force adjust
    uint256 public lockedFunds = 0;
    uint256 public tokensToGenerate = 0;

    function tendTrigger(uint256 gasCost) public view override returns (bool) {
        // Not needed.
        return false;
    }

    function harvestTrigger(uint256 gasCost) public view override returns (bool) {
        StrategyParams memory params = vault.strategies(address(this));

        // Should not trigger if strategy is not activated
        if (params.activation == 0) return false;

        // We need to wait for the lockup to end
        if (!canUnlock()) return false;

        // If we can unlocks or we are ready for the first investment
        // or we are ready to harvest profits
        return true;
    }

    function expectedReturn() public view override returns (uint256) {
        return vault.expectedReturn();
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        return want.balanceOf(address(this));
    }

    function prepareReturn() internal override {
        if (!canUnlock()) return;

        // Time passed! let's unlock the funds and earn profit
        tokensToGenerate = lockedFunds.mul(1000).div(10000);
        unlockFunds();
    }

    function lockFunds() internal {
        timeOfInvestment = block.timestamp;
        lockedFunds = outstanding;
    }

    function unlockFunds() internal {
        lockedFunds = 0;
        timeOfInvestment = uint256(-1);
    }

    function canUnlock() public view returns (bool) {
        return timeOfInvestment.add(lockupPeriod) < block.timestamp;
    }

    function adjustPosition() internal override {
        // Do the investment
        lockFunds();
    }

    function liquidatePosition(uint256 _amount) internal override {
        if (!canUnlock()) return;

        // TODO: What should I do if I can't liquidate?
        // Logic below also doesn't do much afaik, what if reserve > _amount?
        // shouldn't this call exist position?
        if (_amount > reserve) {
            reserve = 0;
        } else {
            reserve = reserve.sub(_amount);
        }
    }

    function exitPosition() internal override {
        // We can only exist when the time passed by
        if (canUnlock()) {
            unlockFunds();
        }
    }

    function prepareMigration(address _newStrategy) internal override {
        want.transfer(_newStrategy, want.balanceOf(address(this)));
    }
}
