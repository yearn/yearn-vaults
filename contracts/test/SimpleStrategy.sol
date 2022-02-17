// SPDX-License-Identifier: GPL-3.0-only
pragma solidity ^0.6.12;

import {Math} from "@openzeppelin/contracts/math/Math.sol";
import {SafeMath} from "@openzeppelin/contracts/math/SafeMath.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import {VaultAPI} from "../BaseStrategy.sol";

interface IStrategy {
    function want() external view returns (address);

    function vault() external view returns (address);

    function delegatedAssets() external view returns (uint256);

    function withdraw(uint256 _amount) external returns (uint256 loss);
}

contract SimpleStrategy is IStrategy {
    using SafeMath for uint256;
    using SafeERC20 for IERC20;

    address public immutable override want;
    address public immutable override vault;
    uint256 public constant override delegatedAssets = 0;
    uint256 public totalDebt;
    uint256 public nextWidthdraw;
    uint256 public nextLoss;

    constructor(address _want, address _vault) public {
        want = _want;
        vault = _vault;
        IERC20(_want).safeApprove(_vault, type(uint256).max);
    }

    function setNext(uint256 _nextWithdraw, uint256 _nextLoss) external {
        nextWidthdraw = _nextWithdraw;
        nextLoss = _nextLoss;
    }

    function withdraw(uint256) external override returns (uint256 loss) {
        loss = nextLoss;
        _withdraw(nextWidthdraw, loss);
    }

    function initialReport() external {
        _report(0, 0, 0);
    }

    function _withdraw(uint256 _withdrawAmount, uint256 _loss) internal {
        totalDebt = totalDebt.sub(_withdrawAmount).sub(_loss);
        IERC20(want).transfer(vault, _withdrawAmount);
    }

    function _reserves() internal view returns (uint256) {
        return IERC20(want).balanceOf(address(this));
    }

    function _report(
        uint256 _gain,
        uint256 _loss,
        uint256 _debtPayment
    ) internal {
        uint256 newTotalDebt = totalDebt.sub(_loss);
        uint256 balanceBefore = _reserves();
        uint256 debtPayment = Math.min(_debtPayment, VaultAPI(vault).debtOutstanding());
        VaultAPI(vault).report(_gain, _loss, debtPayment);
        uint256 balanceAfter = _reserves();
        totalDebt = newTotalDebt.add(balanceAfter).sub(balanceBefore);
    }
}
