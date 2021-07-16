// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.6.0 <0.7.0;

import {ICustomHealthCheck} from "./interfaces/ICustomHealthCheck.sol";
import {StrategyAPI} from "./BaseStrategy.sol";

struct Limits {
    uint256 profitLimitRatio;
    uint256 lossLimitRatio;
    bool exists;
}

contract CommonHealthCheck {
    // Default Settings for all strategies
    uint256 constant MAX_BPS = 10_000;
    uint256 public profitLimitRatio;
    uint256 public lossLimitRatio;
    mapping(address => Limits) public strategiesLimits;

    address public governance;
    address public management;

    mapping(address => address) public checks;
    mapping(address => bool) public disabledCheck;

    modifier onlyGovernance() {
        require(msg.sender == governance, "!authorized");
        _;
    }

    modifier onlyAuthorized() {
        require(msg.sender == governance || msg.sender == management, "!authorized");
        _;
    }

    modifier onlyVault(address strategy) {
        require(msg.sender == StrategyAPI(strategy).vault(), "!authorized");
        _;
    }

    constructor() public {
        governance = msg.sender;
        management = msg.sender;
        profitLimitRatio = 100;
        lossLimitRatio = 1;
    }

    function setGovernance(address _governance) external onlyGovernance {
        require(_governance != address(0));
        governance = _governance;
    }

    function setManagement(address _management) external onlyGovernance {
        require(_management != address(0));
        management = _management;
    }

    function setProfitLimitRatio(uint256 _profitLimitRatio) external onlyAuthorized {
        require(_profitLimitRatio < MAX_BPS);
        profitLimitRatio = _profitLimitRatio;
    }

    function setlossLimitRatio(uint256 _lossLimitRatio) external onlyAuthorized {
        require(_lossLimitRatio < MAX_BPS);
        lossLimitRatio = _lossLimitRatio;
    }

    function setStrategyLimits(
        address _strategy,
        uint256 _profitLimitRatio,
        uint256 _lossLimitRatio
    ) external onlyAuthorized {
        require(_lossLimitRatio < MAX_BPS);
        require(_profitLimitRatio < MAX_BPS);
        strategiesLimits[_strategy] = Limits(_profitLimitRatio, _lossLimitRatio, true);
    }

    function setCheck(address _strategy, address _check) external onlyAuthorized {
        checks[_strategy] = _check;
    }

    function enableCheck(address _strategy) external onlyVault(_strategy) {
        disabledCheck[_strategy] = false;
    }

    function setDisabledCheck(address _strategy, bool disabled) external onlyAuthorized {
        disabledCheck[_strategy] = disabled;
    }

    function doHealthCheck(address _strategy) external view returns (bool) {
        return !disabledCheck[_strategy];
    }

    function check(
        uint256 profit,
        uint256 loss,
        uint256 debtPayment,
        uint256 debtOutstanding,
        uint256 totalDebt
    ) external view returns (bool) {
        address strategy = msg.sender;

        return _runChecks(strategy, profit, loss, debtPayment, debtOutstanding, totalDebt);
    }

    function check(
        address strategy,
        uint256 profit,
        uint256 loss,
        uint256 debtPayment,
        uint256 debtOutstanding,
        uint256 totalDebt
    ) external view returns (bool) {
        require(strategy != address(0));

        return _runChecks(strategy, profit, loss, debtPayment, debtOutstanding, totalDebt);
    }

    function _runChecks(
        address strategy,
        uint256 profit,
        uint256 loss,
        uint256 debtPayment,
        uint256 debtOutstanding,
        uint256 totalDebt
    ) internal view returns (bool) {
        address customCheck = checks[strategy];

        if (customCheck == address(0)) {
            return _executeDefaultCheck(strategy, profit, loss, totalDebt);
        }

        return ICustomHealthCheck(customCheck).check(strategy, profit, loss, debtPayment, debtOutstanding);
    }

    function _executeDefaultCheck(
        address strategy,
        uint256 _profit,
        uint256 _loss,
        uint256 _totalDebt
    ) internal view returns (bool) {
        Limits memory limits = strategiesLimits[strategy];
        uint256 _profitLimitRatio;
        uint256 _lossLimitRatio;
        if (limits.exists) {
            _profitLimitRatio = limits.profitLimitRatio;
            _lossLimitRatio = limits.lossLimitRatio;
        } else {
            _profitLimitRatio = profitLimitRatio;
            _lossLimitRatio = lossLimitRatio;
        }

        if (_profit > ((_totalDebt * _profitLimitRatio) / MAX_BPS)) {
            return false;
        }
        if (_loss > ((_totalDebt * _lossLimitRatio) / MAX_BPS)) {
            return false;
        }
        return true;
    }
}
