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


@pytest.mark.parametrize(
    "getter,setter,caller,val",
    [
        ("strategist", "setStrategist", "gov", None),
        ("rewards", "setRewards", "strategist", None),
        ("keeper", "setKeeper", "strategist", None),
        ("minReportDelay", "setMinReportDelay", "strategist", 1000),
        ("maxReportDelay", "setMaxReportDelay", "strategist", 1000),
        ("profitFactor", "setProfitFactor", "strategist", 1000),
        ("debtThreshold", "setDebtThreshold", "strategist", 1000),
    ],
)
def test_strategy_setParams(
    gov, strategist, strategy, rando, getter, setter, caller, val
):
    if not val:
        # Can't access fixtures, so use None to mean any random address
        val = rando

    prev_val = getattr(strategy, getter)()

    # Only governance or strategist can set this param
    with brownie.reverts():
        getattr(strategy, setter)(val, {"from": rando})

    caller = {"gov": gov, "strategist": strategist}[caller]

    getattr(strategy, setter)(val, {"from": caller})
    assert getattr(strategy, getter)() == val

    getattr(strategy, setter)(prev_val, {"from": caller})
    assert getattr(strategy, getter)() == prev_val


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
