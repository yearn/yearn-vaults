import pytest
import brownie


MAX_BPS = 10_000


@pytest.fixture
def common_health_check(gov, CommonHealthCheck):
    yield gov.deploy(CommonHealthCheck)


def test_set_health_check(gov, rando, strategy, common_health_check):
    with brownie.reverts():
        strategy.setHealthCheck(common_health_check, {"from": rando})
    strategy.setHealthCheck(common_health_check, {"from": gov})


def test_set_do_health_check(gov, rando, strategy):
    with brownie.reverts():
        strategy.setDoHealthCheck(True, {"from": rando})
    strategy.setDoHealthCheck(True, {"from": gov})


def test_strategy_harvest(vault, gov, strategy, token, common_health_check, chain):
    chain.sleep(10)
    strategy.harvest()
    strategy.setHealthCheck(common_health_check, {"from": gov})
    chain.sleep(1)

    chain.snapshot()
    # Small gain doesn't trigger
    balance = strategy.estimatedTotalAssets()
    token.transfer(strategy, balance * 0.02)
    chain.sleep(1)
    strategy.harvest()
    chain.revert()

    # gain is too big
    balance = strategy.estimatedTotalAssets()
    token.transfer(strategy, balance * 0.05)

    with brownie.reverts():
        strategy.harvest()

    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    strategy.harvest()

    chain.revert()

    # small loss doesn't trigger
    balance = strategy.estimatedTotalAssets()
    strategy._takeFunds(balance * 0.01)
    chain.sleep(1)
    strategy.harvest()

    chain.revert()

    # loss is too important
    balance = strategy.estimatedTotalAssets()
    strategy._takeFunds(balance * 0.03)

    with brownie.reverts():
        strategy.harvest()

    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest()


def test_strategy_harvest_custom_limits(
    vault, gov, strategy, token, common_health_check, chain
):
    chain.sleep(10)
    strategy.harvest()
    strategy.setHealthCheck(common_health_check, {"from": gov})
    common_health_check.setStrategyLimits(
        strategy, 5000, 0, {"from": gov}
    )  # big gain no loss
    chain.sleep(1)
    chain.snapshot()

    balance = strategy.estimatedTotalAssets()
    token.transfer(strategy, balance * 0.5)
    chain.sleep(1)
    strategy.harvest()

    chain.revert()
    strategy._takeFunds(1)
    with brownie.reverts():
        strategy.harvest()
