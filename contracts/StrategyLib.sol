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
        uint256 creditThreshold,
        address baseFeeOracle,
        bool forceHarvestTriggerOnce
    ) public view returns (bool) {
        StrategyParams memory params = VaultAPI(vault).strategies(strategy);

        // Trigger regardless of gas price if we've waited too long
        if (block.timestamp.sub(params.lastReport) >= maxReportDelay) return true;

        // check if the base fee gas price is higher than we allow. if it is, block everything below here.
        if (!isBaseFeeAcceptable(baseFeeOracle)) {
            return false;
        }

        // trigger if we want to manually harvest
        if (forceHarvestTriggerOnce) {
            return true;
        }

        // Trigger if we've waited long enough
        if (block.timestamp.sub(params.lastReport) > minReportDelay) return true;

        // harvest our credit if it's above our threshold
        if (VaultAPI(vault).creditAvailable() > creditThreshold) {
            return true;
        }

        // Otherwise, return false
        return false;
    }

    /**
     * @notice
     *  Check if the current network baseFee is below our external target. This
     *  is used in our harvestTrigger to prevent costly harvests during times of
     *  high network congestion.
     *
     *  This baseFee target is configurable via Yearn's yBrain multisig or governance.
     * @return `true` if baseFee is below our target, `false` otherwise or if not setup.
     */
    //
    function isBaseFeeAcceptable(address _oracle) internal view returns (bool) {
        if (_oracle == address(0)) {
            return false;
        } else {
            return IBaseFee(_oracle).isCurrentBaseFeeAcceptable();
        }
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
