from pathlib import Path
import yaml

import pytest
import brownie

from brownie import ZERO_ADDRESS

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent.parent.parent / "ethpm-config.yaml").read_text()
)["version"]


def test_api_adherrance(check_api_adherrance, TestStrategy, interface):
    check_api_adherrance(TestStrategy, interface.StrategyAPI)


def test_strategy_deployment(strategist, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)
    # Addresses
    assert strategy.strategist() == strategist
    assert strategy.rewards() == strategist
    assert strategy.keeper() == strategist
    assert strategy.want() == vault.token()
    assert strategy.apiVersion() == PACKAGE_VERSION
    assert strategy.name() == "TestStrategy " + strategy.apiVersion()
    assert strategy.delegatedAssets() == 0

    assert not strategy.emergencyExit()

    # Should not trigger until it is approved
    assert not strategy.harvestTrigger(0)
    assert not strategy.tendTrigger(0)


def test_strategy_no_reinit(strategist, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)

    with brownie.reverts("Strategy already initialized"):
        strategy.initialize(vault, strategist, strategist, strategist)


def test_strategy_setEmergencyExit(strategy, gov, strategist, rando, chain):
    # Only governance or strategist can set this param
    with brownie.reverts():
        strategy.setEmergencyExit({"from": rando})
    assert not strategy.emergencyExit()

    strategy.setEmergencyExit({"from": gov})
    assert strategy.emergencyExit()

    # Can only set this once
    chain.undo()

    strategy.setEmergencyExit({"from": strategist})
    assert strategy.emergencyExit()


def test_strategy_harvest_permission(
    strategy, gov, strategist, guardian, management, keeper, rando, chain
):
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": strategist})
    chain.sleep(1)
    strategy.harvest({"from": management})
    chain.sleep(1)
    strategy.harvest({"from": guardian})
    chain.sleep(1)
    strategy.harvest({"from": keeper})
    with brownie.reverts():
        strategy.harvest({"from": rando})


@pytest.mark.parametrize(
    "getter,setter,val,gov_allowed,strategist_allowed,authority_error",
    [
        ("rewards", "setRewards", None, False, True, "!strategist"),
        ("keeper", "setKeeper", None, True, True, "!authorized"),
        ("minReportDelay", "setMinReportDelay", 1000, True, True, "!authorized"),
        ("maxReportDelay", "setMaxReportDelay", 2000, True, True, "!authorized"),
        ("profitFactor", "setProfitFactor", 1000, True, True, "!authorized"),
        ("debtThreshold", "setDebtThreshold", 1000, True, True, "!authorized"),
    ],
)
def test_strategy_setParams(
    gov,
    strategist,
    strategy,
    rando,
    getter,
    setter,
    val,
    gov_allowed,
    strategist_allowed,
    authority_error,
):
    if val is None:
        # Can't access fixtures, so use None to mean any random address
        val = rando

    prev_val = getattr(strategy, getter)()

    # None of these params can be set by a rando
    with brownie.reverts(authority_error):
        getattr(strategy, setter)(val, {"from": rando})

    def try_setParam(caller, allowed):
        if allowed:
            getattr(strategy, setter)(val, {"from": caller})
            assert getattr(strategy, getter)() == val

            getattr(strategy, setter)(prev_val, {"from": caller})
            assert getattr(strategy, getter)() == prev_val
        else:
            with brownie.reverts(authority_error):
                getattr(strategy, setter)(val, {"from": caller})

    try_setParam(strategist, strategist_allowed)
    try_setParam(gov, gov_allowed)


def test_set_strategist_authority(strategy, strategist, rando):
    # Testing setStrategist as a strategist isn't clean with test_strategy_setParams,
    # so this test handles it.

    # Only gov or strategist can setStrategist
    with brownie.reverts("!authorized"):
        strategy.setStrategist(rando, {"from": rando})

    # As strategist, set strategist to rando.
    strategy.setStrategist(rando, {"from": strategist})

    # Now the original strategist shouldn't be able to set strategist again
    with brownie.reverts("!authorized"):
        strategy.setStrategist(rando, {"from": strategist})


def test_strategy_setParams_bad_vals(gov, strategist, strategy):
    with brownie.reverts():
        strategy.setKeeper(ZERO_ADDRESS, {"from": gov})
    with brownie.reverts():
        strategy.setRewards(ZERO_ADDRESS, {"from": strategist})


def test_strategist_update(gov, strategist, strategy, rando):
    assert strategy.strategist() == strategist
    strategy.setStrategist(rando, {"from": strategist})
    assert strategy.strategist() == rando
    # Strategist can't change themselves once they update
    with brownie.reverts():
        strategy.setStrategist(strategist, {"from": strategist})
    # But governance can
    strategy.setStrategist(strategist, {"from": gov})
    assert strategy.strategist() == strategist
    # cannot set strategist to zero address
    with brownie.reverts():
        strategy.setStrategist(ZERO_ADDRESS, {"from": gov})
