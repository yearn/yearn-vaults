import brownie


def test_strategy_deployment(strategist, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)
    # Addresses
    assert strategy.strategist() == strategist
    assert strategy.keeper() == strategist
    assert strategy.want() == vault.token()
    assert strategy.reserve() == 0
    assert not strategy.emergencyExit()

    assert strategy.expectedReturn() == 0
    # Should not trigger until it is approved
    assert not strategy.harvestTrigger(0)
    assert not strategy.tendTrigger(0)


def test_vault_setStrategist(strategy, gov, strategist, rando):
    # Only governance or strategist can set this param
    with brownie.reverts():
        strategy.setStrategist(rando, {"from": rando})
    assert strategy.strategist() != rando

    strategy.setStrategist(rando, {"from": gov})
    assert strategy.strategist() == rando

    strategy.setStrategist(strategist, {"from": rando})
    assert strategy.strategist() == strategist


def test_vault_setKeeper(strategy, gov, strategist, rando):
    # Only governance or strategist can set this param
    with brownie.reverts():
        strategy.setKeeper(rando, {"from": rando})
    assert strategy.keeper() != rando

    strategy.setKeeper(rando, {"from": gov})
    assert strategy.keeper() == rando

    # Only governance or strategist can set this param
    with brownie.reverts():
        strategy.setKeeper(rando, {"from": rando})

    strategy.setKeeper(strategist, {"from": strategist})
    assert strategy.keeper() == strategist


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
