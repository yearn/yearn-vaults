// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";
import {StrategyParams, VaultAPI, StrategyAPI} from "./BaseStrategy.sol";

interface IBaseFee {
    function isCurrentBaseFeeAcceptable() external view returns (bool);
}

library StrategyLib {
    using SafeMath for uint256;

    function internalHarvestTrigger(
        address vault,
        address strategy,
        uint256 callCost,
        uint256 minReportDelay,
        uint256 maxReportDelay,
        bool forceHarvestTriggerOnce
    ) public view returns (bool) {
        StrategyParams memory params = VaultAPI(vault).strategies(strategy);

        // Should trigger if hasn't been called in a while
        if (block.timestamp.sub(params.lastReport) >= maxReportDelay) return true;

        // check if the base fee gas price is higher than we allow. if it is, block harvests.
        if (!isBaseFeeAcceptable()) {
            return false;
        }

        // trigger if we want to manually harvest
        if (forceHarvestTriggerOnce) {
            return true;
        }

        // Should not trigger if we haven't waited long enough since previous harvest
        if (block.timestamp.sub(params.lastReport) < minReportDelay) return false;

        // Otherwise, return false
        return false;
    }

    /**
     * @notice
     *  Check if the current network baseFee is below our external target. This
     *  is used in our harvestTrigger to prevent costly harvests during times of
     *  high network congestion.
     *
     *  This baseFee target is configurable via Yearn's yBrain multisig.
     * @return `true` if baseFee is below our target, `false` otherwise.
     */
    //
    function isBaseFeeAcceptable() internal view returns (bool) {
        return IBaseFee(0xb5e1CAcB567d98faaDB60a1fD4820720141f064F).isCurrentBaseFeeAcceptable();
    }

    function internalSetRewards(
        address oldRewards,
        address newRewards,
        address vault
    ) public {
        require(newRewards != address(0));
        VaultAPI(vault).approve(oldRewards, 0);
        VaultAPI(vault).approve(newRewards, type(uint256).max);
    }
}
