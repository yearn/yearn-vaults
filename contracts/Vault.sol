// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.10;

// defaults
// intialzer and overrides
// in LN 557

// import erc20 from openzeppelin-contracts/token/ERC20/ERC20.sol;
import { IERC20 } from "@openzeppelin/contracts/token/IERC20.sol";

interface DetailedERC20 {
    function name () external view returns (string);
    function symbol () external view returns (string);
    function decimals () external view returns (uint256);
}

interface Strategy {
    function want() external view returns (address);
    function vault() external view returns (address);
    function isActive() external view returns (bool);
    function delegatedAssets() external view returns (uint256);
    function estimatedTotalAssets() external view returns (uint256);
    function withdraw(uint256 _amount) external;
    function migrate(address _newStrategy) external;
}

interface HealthCheck {
    function check(address strategy, uint256 profit, uint256 loss, uint256 debtPayment, uint256 debtOutstanding, uint256 totalDebt) external view returns (bool);
    function doHealthCheck(address strategy) external returns (bool);
    function enableCheckt(address strategy) external;
}

struct StrategyParams {
    uint256 performanceFee,
    uint256 activation,
    uint256 debtRatio,
    uint256 minDebtPerHarvest,
    uint256 maxDebtPerHarvest,
    uint256 lastReport,
    uint256 totalDebt,
    uint256 totalGain,
    uint256 totalLoss
}

contract Vault {

    string private _name;
    string private _symbol;

    function name() external view returns (string) {
        return _name;
    }

    function symbol() external view returns (string) {
        return _symbol;
    }

    uint256 private constant MAXIMUM_STRATEGIES = 20;
    uint256 private constant DEGRADATION_COEFFICIENT = 10 ** 18;
    uint256 private constant SET_SIZE = 32;

    mapping (address => StrategyParams) public strategies;

    address private immutable guardian;
    address private immutable management;
    address private healthCheck;

    address private immutable governance;
    address private pendingGovernance;

    address private immutable _self;

    constructor(address token, address governance_, address healthCheck_, address rewards, string name_, string symbol_) public {
        _name = "Vault";
        guardian = msg.sender;
        healthCheck = address(0);

        _name = name_;
        _symbol = symbol_;
        governance = governance_;
        _self = address(this);
    }

    function setName(string name) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        _name = name;
    }

    function setSymbol(string symbol) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        _symbol = symbol;
    }

    function setGovernance(address governance_) external {
        require(msg.sender == _governance, "This may only be called by the current governance address.");
        
        // emit NewPendingGovernance
        pendingGovernance = governance_;
    }

    function setManagement(address management_) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        management = management_;

        // emit UpdateManagement
    }

    function setRewards(address rewards_) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        require(rewards_ != address(0) || _self);

        rewards = rewards_;

        // emit UpdateRewards
    }

    function setLockedProfitDegradation(uint256 degradation) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        require(degradation <= DEGRADATION_COEFFICIENT, "This may only be called by governance.");

        lockedProfitDegradation = degradation;

        // emit LockedProfitDegradationUpdated(degradation);
    }

    function setDepositLimit(uint256 limit) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        depoistLimit = limit;

        // emit UpdateDepositLimit(limit);
    }

    function setPerformanceFee(uint256 fee) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        assert(fee <= MAX_BPS / 2);
        performance = fee;

        // emit UpdatePerformanceFee(fee);
    }

    function setManagementFee(uint256 fee) external {
        require(msg.sender == _governance, "This may only be called by governance.");
        assert(fee <= MAX_BPS);
        performance = fee;

        // emit UpdateManagementFee(fee);
    }

    function setGuardian(address guardian_) external {
        require(msg.sender == (guardian || _governance), "This may only be called by governance or the guardian.");
        guardian = guardian_;
        // emit UpdateGuardian(guardian);
    }

    function setEmergencyShutdown(bool active) external {
        if (active)
            require(msg.sender == (guardian || _governance), "This may only be called by governance or the guardian.");
        else
            require(msg.sender == _governance, "This may only be called by governance or the guardian.");

        emergencyShutdown = active;
        // emit EmergencyShutdown(active);
    }

    function setWithdrawalQueue(queue calldata address[]) external {
        require(msg.sender == guardian || _governance, "Only guardian or governance can set withdrawl queue");

        for (uint i = 0; i < MAXIMUM_STRATEGIES; i++) {
            if (queue[i] == address(0)) {
                assert(withdrawalQueue[i] == address(0));
                break;
            }
            
            assert(withdrawalQueue[i] != address(0));
            assert(strategies[queue[i]].activation > 0)
        
            for (uint j = 0; j < SET_SIZE; j++) {
                uint256 idx = 
                assert(set[idx] != queue[i]);

                if (set[idx] == address(0)) {
                    set[idx] = queue[i];
                    break;
                }
            }
        
            withdrawalQueue[i] = queue[i];
        }

        // emit UpdateWithdrawalQueue(queue);
    }

    function erc20_safe_transfer(address token, address receiver, uint256 amount) internal {
        // wrap openzeppelin-contracts/token/ERC20/ERC20.sol:safeTransfer
    }

    function erc20_safe_transfer_from(address token, address receiver, uint256 amount) external {
    }

    function _transfer(address token, address receiver, uint256 amount) internal {
    }

    function transfer(address receiver, uint256 amount) external {
    }

    function transferFrom(address sender, address receiver, uint256 amount) external {
    }

    function _totalAssets() internal view returns (uint256) {
    }

    function totalAssets() external view returns (uint256) {
    }

    function _calculateLockedProfit() internal view returns (uint256) {
    }

    function _freeFunds() internal view returns (uint256) {
    }

    function _issueSharesForAmount(address to, uint256 amount) internal returns (uint256) {

    }

    function withdraw(uint256 amount) external returns (uint256) {
        uint256 _amount = type(uint256).max;
        address recipient = msg.sender;
    }

    function _shareValue(uint256 shares) internal view returns (uint256) {
        
    }

    function _sharesForAmount(uint256 shares) internal view returns (uint256) {
        
    }

    function maxAvailableShares() external view returns (uint256) {
    }

    function _reportLoss(address strategy, uint256 loss) internal {
        
    }

    function withdraw(uint256 maxShares, address recipient, uint256 maxLoss) external {
        
    }

    function pricePerShare() external view returns (uint256) {
    }

    function _organiseWithdrawalQueue() internal {
        
    }

    function addStrategy(address strategy, uint256 debtRatio, uint256 minDebtPerHarvest, uint256 maxDebtPerHarvest, uint256 performanceFee, uint256 profitLimitRatio, uint256 lossLimitRatio) external {
        
    }

    function updateStrategyDebtRatio(address strategy, uint256 debtRatio) external {
        
    }

    function updateStrategyMinDebtPerHarvest(address strategy, uint256 minDebtPerHarvest) external {
        
    }

    function updateStrategyPerformanceFee(address strategy, uint256 performanceFee) external {
        
    }

    function setHealthCheck(address _healthCheck) external {
        
    }

    function _revokeStrategy(address strategy) internal {
        
    }

    function migrate(address oldVersion, address newVersion) external {
        
    }

    function revokeStrategy() external {
        address strategy = msg.sender;
    }

    event Deposit();
    event Withdrawal();
    event Sweep();
    event LockedProfitDegradationUpdated();
    event StrategyAdded();
}