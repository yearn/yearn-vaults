import pytest
import brownie

FEE_MAX = 10_000


def test_performance_fees(chain, gov, vault, token, TestStrategy, rewards, strategist):
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(450, {"from": gov})

    assert vault.balanceOf(rewards) == 0
    assert vault.balanceOf(strategist) == 0

    strategy = strategist.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 2_000, 1000, 50, {"from": gov})
    token.transfer(strategy, 10 ** 8, {"from": gov})
    chain.sleep(1)  # Reverts if no delta time
    strategy.harvest({"from": strategist})

    assert vault.balanceOf(rewards) == 0.045 * 1e8
    assert vault.balanceOf(strategist) == 0.005 * 1e8


def test_zero_fees(chain, gov, vault, token, TestStrategy, rewards, strategist):
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})

    assert vault.balanceOf(rewards) == 0
    assert vault.balanceOf(strategist) == 0

    strategy = strategist.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 2_000, 1000, 0, {"from": gov})
    token.transfer(strategy, 10 ** 8, {"from": gov})
    chain.sleep(1)  # Reverts if no delta time
    strategy.harvest({"from": strategist})

    assert vault.managementFee() == 0
    assert vault.performanceFee() == 0
    assert vault.strategies(strategy).dict()["performanceFee"] == 0
    assert vault.balanceOf(rewards) == 0
    assert vault.balanceOf(strategist) == 0


def test_max_fees(gov, vault, token, TestStrategy, rewards, strategist):
    # performance fee should not be higher than MAX
    vault.setPerformanceFee(FEE_MAX, {"from": gov})
    with brownie.reverts():
        vault.setPerformanceFee(FEE_MAX + 1, {"from": gov})

    # management fee should not be higher than MAX
    vault.setManagementFee(FEE_MAX, {"from": gov})

    with brownie.reverts():
        vault.setManagementFee(FEE_MAX + 1, {"from": gov})

    # addStrategy should check for MAX FEE
    strategy = strategist.deploy(TestStrategy, vault)
    with brownie.reverts():
        vault.addStrategy(strategy, 2_000, 1000, FEE_MAX + 1, {"from": gov})

    # updateStrategyPerformanceFee should check for max to be MAX FEE - current performance fee
    vault.addStrategy(strategy, 2_000, 1000, 0, {"from": gov})
    vault_performance_fee = vault.performanceFee()
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(
            strategy, FEE_MAX - vault_performance_fee + 1, {"from": gov}
        )
