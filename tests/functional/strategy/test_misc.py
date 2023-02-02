import pytest
import brownie

MAX_UINT256 = 2**256 - 1


def test_harvest_tend_authority(gov, keeper, strategist, strategy, rando, chain):
    # Only keeper, strategist, or gov can call tend
    strategy.tend({"from": keeper})
    strategy.tend({"from": strategist})
    strategy.tend({"from": gov})
    with brownie.reverts():
        strategy.tend({"from": rando})

    # Only keeper, strategist, or gov can call harvest
    strategy.harvest({"from": keeper})

    chain.sleep(1)
    strategy.harvest({"from": strategist})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    with brownie.reverts():
        strategy.harvest({"from": rando})


def test_harvest_tend_trigger(chain, gov, vault, token, TestStrategy, base_fee_oracle):
    strategy = gov.deploy(TestStrategy, vault)

    # setup our base fee oracle for testing
    strategy.setBaseFeeOracle(base_fee_oracle, {"from": gov})

    # Trigger doesn't work until strategy is attached and funds added
    assert not strategy.harvestTrigger(0)

    # Must wait at least the minimum amount of time for it to be active
    vault.addStrategy(strategy, 2_000, 0, MAX_UINT256, 50, {"from": gov})
    last_report = vault.strategies(strategy).dict()["lastReport"]
    strategy.harvest({"from": gov})  # Sends funds into strategy
    strategy.setMinReportDelay(10, {"from": gov})
    assert not strategy.harvestTrigger(0)

    # After maxReportDelay has expired,  doesn't matter
    last_report = vault.strategies(strategy).dict()["lastReport"]
    chain.mine(timedelta=strategy.maxReportDelay() - (chain.time() - last_report))
    assert strategy.harvestTrigger(MAX_UINT256)
    strategy.harvest({"from": gov})  # Resets the reporting

    # Will fail if our gas oracle blocks it
    last_report = vault.strategies(strategy).dict()["lastReport"]
    chain.mine(timedelta=strategy.maxReportDelay() - (chain.time() - last_report))
    assert strategy.harvestTrigger(0)
    base_fee_oracle.setManualBaseFeeBool(False, {"from": gov})
    assert not strategy.harvestTrigger(0)
    base_fee_oracle.setManualBaseFeeBool(True, {"from": gov})
    assert strategy.harvestTrigger(0)
    strategy.harvest({"from": gov})  # Resets the reporting

    # harvest if we have any credit at all, first add loose want
    assert not strategy.harvestTrigger(0)
    last_report = vault.strategies(strategy).dict()["lastReport"]
    chain.mine(timedelta=strategy.minReportDelay() - (chain.time() - last_report))
    token.approve(vault, token.balanceOf(gov) // 20, {"from": gov})
    vault.deposit(token.balanceOf(gov) // 20, {"from": gov})
    strategy.setCreditThreshold(1, {"from": gov})
    assert strategy.harvestTrigger(0)
    strategy.harvest({"from": gov})  # Resets the reporting

    # can force it as long as we have assets and gas is okay
    assert not strategy.harvestTrigger(0)
    strategy.setForceHarvestTriggerOnce(True, {"from": gov})
    assert strategy.harvestTrigger(0)
    strategy.setForceHarvestTriggerOnce(False, {"from": gov})
    assert not strategy.harvestTrigger(0)

    # Check that trigger works in emergency exit mode
    strategy.setEmergencyExit({"from": gov})
    last_report = vault.strategies(strategy).dict()["lastReport"]
    chain.mine(timedelta=strategy.maxReportDelay() - (chain.time() - last_report))
    assert strategy.harvestTrigger(MAX_UINT256)

    # Stops after it runs out of balance
    while strategy.harvestTrigger(0):
        chain.sleep(1)
        chain.mine(1)
        strategy.harvest({"from": gov})

    assert strategy.estimatedTotalAssets() == 0


def test_sweep_authority(
    gov, vault, rando, strategy, strategist, guardian, management, keeper, other_token
):
    assert rando != gov
    assert strategist != gov
    assert keeper != gov
    assert guardian != gov
    assert management != gov

    # Random people cannot sweep
    with brownie.reverts():
        strategy.sweep(other_token, {"from": rando})

    # Strategist cannot sweep
    with brownie.reverts():
        strategy.sweep(other_token, {"from": strategist})

    # Keeper cannot sweep
    with brownie.reverts():
        strategy.sweep(other_token, {"from": keeper})

    # Guardians cannot sweep
    with brownie.reverts():
        strategy.sweep(other_token, {"from": guardian})

    # Management cannot sweep
    with brownie.reverts():
        strategy.sweep(other_token, {"from": management})

    # Governance can sweep
    strategy.sweep(other_token, {"from": gov})


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token, 18)


def test_sweep(gov, vault, strategy, rando, token, other_token):
    # Strategy want token doesn't work
    token.transfer(strategy, token.balanceOf(gov), {"from": gov})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts():
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts():
        strategy.sweep(vault.address, {"from": gov})

    # Protected token doesn't work
    with brownie.reverts():
        strategy.sweep(strategy.protectedToken(), {"from": gov})

    # But any other random token works
    other_token.transfer(strategy, other_token.balanceOf(gov), {"from": gov})
    assert other_token.address != strategy.want()
    assert other_token.balanceOf(strategy) > 0
    assert other_token.balanceOf(gov) == 0
    # Not any random person can do this
    with brownie.reverts():
        strategy.sweep(other_token, {"from": rando})

    before = other_token.balanceOf(strategy)
    strategy.sweep(other_token, {"from": gov})
    assert other_token.balanceOf(strategy) == 0
    assert other_token.balanceOf(gov) == before
    assert other_token.balanceOf(rando) == 0


def test_reject_ether(gov, strategy):
    # These functions should reject any calls with value
    for func, args in [
        ("setStrategist", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setKeeper", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("tend", []),
        ("harvest", []),
        ("migrate", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setEmergencyExit", []),
        ("sweep", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
    ]:
        with brownie.reverts():
            # NOTE: gov can do anything
            getattr(strategy, func)(*args, {"from": gov, "value": 1})

    # Fallback fails too
    with brownie.reverts():
        gov.transfer(strategy, 1)


def test_set_metadataURI(gov, strategy, strategist, rando):
    assert strategy.metadataURI() == ""  # Empty by default
    strategy.setMetadataURI("ipfs://test", {"from": gov})
    assert strategy.metadataURI() == "ipfs://test"
    strategy.setMetadataURI("ipfs://test2", {"from": gov})
    assert strategy.metadataURI() == "ipfs://test2"
    strategy.setMetadataURI("ipfs://test3", {"from": strategist})
    assert strategy.metadataURI() == "ipfs://test3"
    with brownie.reverts():
        strategy.setMetadataURI("ipfs://fake", {"from": rando})


def test_reduce_debt_ratio(strategy, vault, gov, chain):
    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["totalDebt"] > 0
    old_debt_ratio = vault.strategies(strategy).dict()["debtRatio"]
    vault.updateStrategyDebtRatio(strategy, old_debt_ratio // 2, {"from": gov})

    assert vault.debtOutstanding(strategy) > 0
