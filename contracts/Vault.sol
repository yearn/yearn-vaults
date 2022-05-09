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

    event Deposit();
    event Withdrawal();
    event Sweep();
    event LockedProfitDegradationUpdated();
    event StrategyAdded();
}