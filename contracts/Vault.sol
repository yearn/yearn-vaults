// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.13;

// defaults
// intialzer and overrides
// in LN 557

import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

// it is not necessary to implement this since these attributes are included in the base contract (ERC20) since OZ v3.0
// interface DetailedERC20 {
//     function name () external view returns (string calldata);
//     function symbol () external view returns (string calldata);
//     function decimals () external view returns (uint256);
// }

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
    uint256 performanceFee;
    uint256 activation;
    uint256 debtRatio;
    uint256 minDebtPerHarvest;
    uint256 maxDebtPerHarvest;
    uint256 lastReport;
    uint256 totalDebt;
    uint256 totalGain;
    uint256 totalLoss;
}

// TODO: Implements ERC20
contract Vault is ERC20 {

    // string public name;
    // string public symbol;

    using SafeERC20 for IERC20;

    IERC20 public immutable token;

    mapping (address => StrategyParams) public strategies;
    uint256 private constant MAXIMUM_STRATEGIES = 20;
    uint256 private constant DEGRADATION_COEFFICIENT = 10 ** 18;
    uint256 private constant SET_SIZE = 32;
    address[] public withdrawalQueue;
    bool public emergencyShutdown;

    address private governance;
    address private guardian;
    address private management;
    address private pendingGovernance;
    address private healthCheck;

    address private immutable _self;

    uint256 public depositLimit;
    uint256 public debtRatio;
    uint256 public totalDebt;
    uint256 public lastReport;
    uint256 public activation;
    uint256 public lockedProfit;
    uint256 public lockedProfitDegradation;
    address public rewards;
    uint256 public managementFee;
    uint256 public performanceFee;
    uint256 constant MAX_BPS = 10_000;
    uint256 constant SECS_PER_YEAR = 31_556_952;  // 365.2425 days

    constructor(address token_, address governance_, address rewards_, string memory nameOverride, string memory symbolOverride) public {
        _name = "Vault";
        
        governance = governance_;
        _name = nameOverride;
        _symbol = symbolOverride;
        guardian = msg.sender;
        management = msg.sender;
        healthCheck = address(0);

        token = IERC20(token_);
        performanceFee = 1000;
        managementFee = 200;

        lastReport = block.timestamp;
        activation = block.timestamp;
        lockedProfitDegradation = uint256(DEGRADATION_COEFFICIENT * 46 / 10 ** 6);

        _self = address(this);
    }

    function setName(string calldata name_) external {
        require(msg.sender == governance, "This may only be called by governance.");
        _name = name_;
    }

    function setSymbol(string calldata symbol_) external {
        require(msg.sender == governance, "This may only be called by governance.");
        _symbol = symbol_;
    }

    function setGovernance(address governance_) external {
        require(msg.sender == governance, "This may only be called by the current governance address.");
        
        emit NewPendingGovernance(governance_);
        pendingGovernance = governance_;
    }

    function setManagement(address management_) external {
        require(msg.sender == governance, "This may only be called by governance.");
        management = management_;

        emit UpdateManagement(management_);
    }

    function setRewards(address rewards_) external {
        require(msg.sender == governance, "This may only be called by governance.");
        assert(rewards_ != address(0) || rewards_ != _self);

        rewards = rewards_;

        emit UpdateRewards(rewards_);
    }

    function setLockedProfitDegradation(uint256 degradation) external {
        require(msg.sender == governance, "This may only be called by governance.");
        require(degradation <= DEGRADATION_COEFFICIENT, "This may only be called by governance.");

        lockedProfitDegradation = degradation;

        emit LockedProfitDegradationUpdated(degradation);
    }

    function setDepositLimit(uint256 limit) external {
        require(msg.sender == governance, "This may only be called by governance.");
        depositLimit = limit;

        emit UpdateDepositLimit(limit);
    }

    function setPerformanceFee(uint256 fee) external {
        require(msg.sender == governance, "This may only be called by governance.");
        assert(fee <= MAX_BPS / 2);
        performanceFee = fee;

        emit UpdatePerformanceFee(fee);
    }

    function setManagementFee(uint256 fee) external {
        require(msg.sender == governance, "This may only be called by governance.");
        assert(fee <= MAX_BPS);
        managementFee = fee;

        emit UpdateManagementFee(fee);
    }

    function setGuardian(address guardian_) external {
        require(msg.sender == guardian || msg.sender == governance, "This may only be called by governance or the guardian.");
        guardian = guardian_;

        emit UpdateGuardian(guardian_);
    }

    function setEmergencyShutdown(bool active) external {
        if (active)
            require(msg.sender == guardian || msg.sender == governance, "This may only be called by governance or the guardian.");
        else
            require(msg.sender == governance, "This may only be called by governance or the guardian.");

        emergencyShutdown = active;
        emit EmergencyShutdown(active);
    }

    function setWithdrawalQueue(address[] calldata queue) external {
        require(msg.sender == guardian || msg.sender == governance, "Only guardian or governance can set withdrawl queue");
        address[] memory set = new address[](SET_SIZE);

        for (uint i = 0; i < MAXIMUM_STRATEGIES; i++) {
            if (queue[i] == address(0)) {
                assert(withdrawalQueue[i] == address(0));
                break;
            }
            
            assert(withdrawalQueue[i] != address(0));
            assert(strategies[queue[i]].activation > 0);

            // # NOTE: `key` is first `log_2(SET_SIZE)` bits of address (which is a hash)
            // key: uint256 = bitwise_and(convert(queue[i], uint256), SET_SIZE - 1)
            // uint256 key = uint256(queue[i]) & SET_SIZE - 1;
            uint256 key = SET_SIZE - 1; // hack to compile
            
            for (uint j = 0; j < SET_SIZE; j++) {
                uint256 idx = (key + j) % SET_SIZE;
                // assert(set[idx] != queue[i]);

                if (set[idx] == address(0)) {
                    set[idx] = queue[i];
                    break;
                }
            }
        
            withdrawalQueue[i] = queue[i];
        }

        // emit UpdateWithdrawalQueue(queue);
    }

    function erc20_safe_transfer(address token_, address receiver, uint256 amount) internal {
        IERC20(token_).safeTransfer(receiver, amount);
    }

    function erc20_safe_transfer_from(address token_, address sender, address receiver, uint256 amount) external {
        IERC20(token_).safeTransferFrom(sender, receiver, amount);
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

    function addStrategy(address strategy, uint256 debtRatio_, uint256 minDebtPerHarvest, uint256 maxDebtPerHarvest, uint256 performanceFee_, uint256 profitLimitRatio, uint256 lossLimitRatio) external {
        
    }

    function updateStrategyDebtRatio(address strategy, uint256 debtRatio_) external {
        
    }

    function updateStrategyMinDebtPerHarvest(address strategy, uint256 minDebtPerHarvest) external {
        
    }

    function updateStrategyPerformanceFee(address strategy, uint256 performanceFee_) external {
        
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

    event Transfer(address indexed sender, address indexed receiver, uint256 value);

    event Approval(address indexed owner, address indexed spender, uint256 value);

    event Deposit(address indexed recipient, uint256 shares, uint256 amount);
    
    event Withdraw(address indexed recipient, uint256 shares, uint256 amount);
    
    event Sweep(address indexed token, uint256 amount);
    
    event LockedProfitDegradationUpdated(uint256 value);

    /// @param debtRatio: Maximum borrow amount (in BPS of total assets)
    /// @param minDebtPerHarvest: Lower limit on the increase of debt since last harvest
    /// @param maxDebtPerHarvest: Upper limit on the increase of debt since last harvest
    /// @param performanceFee: Strategist's fee (basis points)
    event StrategyAdded(address indexed strategy, uint256 debtRatio, uint256 minDebtPerHarvest, uint256 maxDebtPerHarvest, uint256 performanceFee);
    
    event StrategyReported(address indexed strategy, uint256 gain, uint256 loss, uint256 debtPaid, uint256 totalGain, uint256 totalLoss, uint256 totalDebt, uint256 debtAdded, uint256 debtRatio);
    
    /// @param governance: New active governance
    event UpdateGovernance(address governance);

    /// @param governance: New pending governance
    event NewPendingGovernance(address governance);
    
    /// @param management: New active manager
    event UpdateManagement(address management);
    
    /// @param rewards: New active rewards recipient
    event UpdateRewards(address rewards);
    
    /// @param depositLimit: New active deposit limit
    event UpdateDepositLimit(uint256 depositLimit);
    
    /// @param performanceFee: New active performance fee
    event UpdatePerformanceFee(uint256 performanceFee);
    
    /// @param managementFee: New active management fee
    event UpdateManagementFee(uint256 managementFee);

    /// @param guardian: Address of the active guardian
    event UpdateGuardian(address guardian);
    
    /// @param active: New emergency shutdown state (if false, normal operation enabled)
    event EmergencyShutdown(bool active);
    
    /// @param queue: New active withdrawal queue
    event UpdateWithdrawalQueue(address[MAXIMUM_STRATEGIES] queue);
    
    /// @param strategy: Address of the strategy for the debt ratio adjustment
    /// @param debtRatio: The new debt limit for the strategy (in BPS of total assets)
    event StrategyUpdateDebtRatio(address indexed strategy, uint256 debtRatio);
    
    /// @param strategy: Address of the strategy for the rate limit adjustment
    /// @param minDebtPerHarvest: Lower limit on the increase of debt since last harvest
    event StrategyUpdateMinDebtPerHarvest(address indexed strategy, uint256 minDebtPerHarvest);
    
    /// @param strategy: Address of the strategy for the rate limit adjustment
    /// @param maxDebtPerHarvest: Upper limit on the increase of debt since last harvest
    event StrategyUpdateMaxDebtPerHarvest(address indexed strategy, uint256 maxDebtPerHarvest);
    
    /// @param strategy: Address of the strategy for the rate limit adjustment
    /// @param performanceFee: The new performance fee for the strategy
    event StrategyUpdatePerformanceFee(address indexed strategy, uint256 performanceFee);
    
    /// @param oldVersion: Old version of the strategy to be migrated
    /// @param newVersion: New version of the strategy
    event StrategyMigrated(address indexed oldVersion, address indexed newVersion);
    
    /// @param strategy: Address of the strategy that is revoked
    event StrategyRevoked(address indexed strategy);
    
    /// @param strategy: Address of the strategy that is removed from the withdrawal queue
    event StrategyRemovedFromQueue(address indexed strategy);
    
    /// @param strategy: Address of the strategy that is added to the withdrawal queue
    event StrategyAddedToQueue(address indexed strategy);

    event UpdateHealthCheck(address indexed healthCheck);
}