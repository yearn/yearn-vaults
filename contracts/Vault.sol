// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.10;

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

contract Vault {
    
}