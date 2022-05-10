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

    constructor(address token, address governance_, address healthCheck, address rewards, string name_, string symbol_) public {
        _name = "Vault";
        guardian = msg.sender;
        healthCheck = address(0);

        _name = name_;
        _symbol = symbol_;

        governance = governance;
    }

    function setName(string name) external {
        require(msg.sender == _governance, "Only governance can set the name");
        _name = name;
    }

    function setManagement(address management_) external {

    }

    function setRewards(address rewards_) external {
    }

    function setLockedProfitDegradation(uint256 degradation) external {
    }

    function setDepositLimit(uint256 limit) external {
    }

    function setPerformanceFee(uint256 fee) external {
    }

    function setManagementFee(uint256 fee) external {
    }

    function setGuardian(address guardian_) external {
    }

    function setEmergencyShutdown(bool active) external {
        if (active)
            require(msg.sender == guardian || _governance, "Only guardian or governance can set emergency shutdown");
        else
            require(msg.sender == _governance, "Only governance can set the emergency shutdown");

        emergencyShutdown = active;
    }

    function setWithdrawalQueue(queue calldata address[]) external {
        require(msg.sender == guardian || _governance, "Only guardian or governance can set withdrawl queue");

        for (uint i = 0; i < MAXIMUM_STRATEGIES; i++) {

        }
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
    event StrategyMigrated(address indexed oldVersion, address newVersion);
    
    /// @param strategy: Address of the strategy that is revoked
    event StrategyRevoked(address indexed strategy);
    
    /// @param strategy: Address of the strategy that is removed from the withdrawal queue
    event StrategyRemovedFromQueue(address indexed strategy);
    
    /// @param strategy: Address of the strategy that is added to the withdrawal queue
    event StrategyAddedToQueue(address indexed strategy);

    event UpdateHealthCheck(address healthCheck);
}