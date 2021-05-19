// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.3;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {BaseStrategyInitializable, StrategyParams, VaultAPI} from "../BaseStrategy.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/*
 * This Strategy serves as both a mock Strategy for testing, and an example
 * for integrators on how to use BaseStrategy
 */

contract TestStrategy is BaseStrategyInitializable {
    bool public doReentrancy;
    bool public delegateEverything;
    using SafeERC20 for IERC20;

    // Some token that needs to be protected for some reason
    // Initialize this to some fake address, because we're just using it
    // to test `BaseStrategy.protectedTokens()`
    address public constant protectedToken = address(0xbad);

    constructor(address _vault) BaseStrategyInitializable(_vault) {}

    function name() external override view returns (string memory) {
        return string(abi.encodePacked("TestStrategy ", apiVersion()));
    }

    // NOTE: This is a test-only function to simulate delegation
    function _toggleDelegation() public {
        delegateEverything = !delegateEverything;
    }

    function delegatedAssets() external override view returns (uint256) {
        if (delegateEverything) {
            return vault.strategies(address(this)).totalDebt;
        } else {
            return 0;
        }
    }

    // NOTE: This is a test-only function to simulate losses
    function _takeFunds(uint256 amount) public {
        want.safeTransfer(msg.sender, amount);
    }

    // NOTE: This is a test-only function to enable reentrancy on withdraw
    function _toggleReentrancyExploit() public {
        doReentrancy = !doReentrancy;
    }

    // NOTE: This is a test-only function to simulate a wrong want token
    function _setWant(IERC20 _want) public {
        want = _want;
    }

    function ethToWant(uint256 amtInWei) public override view returns (uint256) {
        return amtInWei; // 1:1 conversion for testing
    }

    function estimatedTotalAssets() public override view returns (uint256) {
        // For mock, this is just everything we have
        return want.balanceOf(address(this));
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // During testing, send this contract some tokens to simulate "Rewards"
        uint256 totalAssets = want.balanceOf(address(this));
        uint256 totalDebt = vault.strategies(address(this)).totalDebt;
        if (totalAssets > _debtOutstanding) {
            _debtPayment = _debtOutstanding;
            totalAssets = totalAssets - _debtOutstanding;
        } else {
            _debtPayment = totalAssets;
            totalAssets = 0;
        }
        totalDebt = totalDebt - _debtPayment;

        if (totalAssets > totalDebt) {
            _profit = totalAssets - totalDebt;
        } else {
            _loss = totalDebt - totalAssets;
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        // Whatever we have "free", consider it "invested" now
    }

    function liquidatePosition(uint256 _amountNeeded) internal override returns (uint256 _liquidatedAmount, uint256 _loss) {
        if (doReentrancy) {
            // simulate a malicious protocol or reentrancy situation triggered by strategy withdraw interactions
            uint256 stratBalance = VaultAPI(address(vault)).balanceOf(address(this));
            VaultAPI(address(vault)).withdraw(stratBalance, address(this));
        }

        uint256 totalDebt = vault.strategies(address(this)).totalDebt;
        uint256 totalAssets = want.balanceOf(address(this));
        if (_amountNeeded > totalAssets) {
            _liquidatedAmount = totalAssets;
            _loss = _amountNeeded - totalAssets;
        } else {
            // NOTE: Just in case something was stolen from this contract
            if (totalDebt > totalAssets) {
                _loss = totalDebt - totalAssets;
                if (_loss > _amountNeeded) _loss = _amountNeeded;
            }
            _liquidatedAmount = _amountNeeded;
        }
    }

    function prepareMigration(address _newStrategy) internal override {
        // Nothing needed here because no additional tokens/tokenized positions for mock
    }

    function protectedTokens() internal override view returns (address[] memory) {
        address[] memory protected = new address[](1);
        protected[0] = protectedToken;
        return protected;
    }

    function liquidateAllPositions() internal override returns (uint256 amountFreed) {
        uint256 totalAssets = want.balanceOf(address(this));
        amountFreed = totalAssets;
    }
}
