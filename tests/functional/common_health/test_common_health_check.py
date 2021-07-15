import pytest
import brownie


MAX_BPS = 10_000


@pytest.fixture
def common_health_check(gov, CommonHealthCheck):
    yield gov.deploy(CommonHealthCheck)


def test_set_goverance(gov, rando, common_health_check):
    with brownie.reverts():
        common_health_check.setGovernance(rando, {"from": rando})
    common_health_check.setGovernance(rando, {"from": gov})


def test_set_management(gov, rando, common_health_check):
    with brownie.reverts():
        common_health_check.setManagement(rando, {"from": rando})
    common_health_check.setManagement(rando, {"from": gov})


def test_set_profit_limit_ratio(gov, rando, common_health_check):
    with brownie.reverts():
        common_health_check.setProfitLimitRatio(10, {"from": rando})

    common_health_check.setProfitLimitRatio(10, {"from": gov})

    with brownie.reverts():
        common_health_check.setProfitLimitRatio(MAX_BPS + 1, {"from": gov})


def test_set_stop_loss_limit_ratio(gov, rando, common_health_check):
    with brownie.reverts():
        common_health_check.setlossLimitRatio(10, {"from": rando})

    common_health_check.setlossLimitRatio(10, {"from": gov})

    with brownie.reverts():
        common_health_check.setlossLimitRatio(MAX_BPS + 1, {"from": gov})


def test_set_stop_loss_limit_ratio(gov, rando, strategy, common_health_check):
    with brownie.reverts():
        common_health_check.setStrategyLimits(strategy, 10, 10, {"from": rando})

    common_health_check.setStrategyLimits(strategy, 10, 10, {"from": gov})

    with brownie.reverts():
        common_health_check.setStrategyLimits(strategy, 10, MAX_BPS + 1, {"from": gov})


def test_set_set_check(gov, rando, strategy, common_health_check):
    with brownie.reverts():
        common_health_check.setCheck(strategy, strategy, {"from": rando})

    common_health_check.setCheck(strategy, strategy, {"from": gov})
