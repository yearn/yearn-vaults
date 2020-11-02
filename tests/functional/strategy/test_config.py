from pathlib import Path
import yaml

import pytest
import brownie

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent.parent.parent / "ethpm-config.yaml").read_text()
)["version"]


def test_strategy_deployment(strategist, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)
    # Addresses
    assert strategy.strategist() == strategist
    assert strategy.keeper() == strategist
    assert strategy.want() == vault.token()
    assert strategy.apiVersion() == PACKAGE_VERSION
    assert strategy.name() == "TestStrategy"

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
    "getter,setter,val",
    [
        ("strategist", "setStrategist", None),
        ("keeper", "setKeeper", None),
        ("minReportDelay", "setMinReportDelay", 1000),
        ("profitFactor", "setProfitFactor", 1000),
        ("debtThreshold", "setDebtThreshold", 1000),
    ],
)
def test_strategy_setParams(gov, strategist, strategy, rando, getter, setter, val):
    if not val:
        # Can't access fixtures, so use None to mean any random address
        val = rando

    prev_val = getattr(strategy, getter)()

    # Only governance or strategist can set this param
    with brownie.reverts():
        getattr(strategy, setter)(val, {"from": rando})

    getattr(strategy, setter)(val, {"from": strategist})
    assert getattr(strategy, getter)() == val

    if getter == "strategist":
        # Strategist can't change themselves once they update
        with brownie.reverts():
            strategy.setStrategist(strategist, {"from": strategist})

    getattr(strategy, setter)(prev_val, {"from": gov})
    assert getattr(strategy, getter)() == prev_val
