import pytest
import brownie

MAX_UINT256 = 2 ** 256 - 1


def test_harvest_tend_authority(gov, keeper, strategist, strategy, rando, chain):
    # Only keeper, strategist, or gov can call tend
    strategy.tend({"from": keeper})
    strategy.tend({"from": strategist})
    strategy.tend({"from": gov})
    with brownie.reverts("!authorized"):
        strategy.tend({"from": rando})

    # Only keeper, strategist, or gov can call harvest
    chain.sleep(1)
    strategy.harvest({"from": keeper})

    chain.sleep(1)
    strategy.harvest({"from": strategist})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    with brownie.reverts("!authorized"):
        strategy.harvest({"from": rando})


def test_harvest_tend_trigger(chain, gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    # Trigger doesn't work until strategy is added
    assert not strategy.harvestTrigger(0)

    vault.addStrategy(strategy, 2_000, 0, MAX_UINT256, 50, {"from": gov})
    last_report = vault.strategies(strategy).dict()["lastReport"]
    strategy.setMinReportDelay(10, {"from": gov})
    # Must wait at least the minimum amount of time for it to be active
    assert not strategy.harvestTrigger(0)
    chain.mine(timedelta=strategy.minReportDelay() - (chain.time() - last_report))
    assert strategy.harvestTrigger(0)

    # Not high enough profit:cost ratio
    assert not strategy.harvestTrigger(MAX_UINT256 // strategy.profitFactor())

    # After maxReportDelay has expired, profit doesn't matter
    chain.mine(timedelta=strategy.maxReportDelay() - (chain.time() - last_report))
    assert strategy.harvestTrigger(MAX_UINT256)
    strategy.harvest({"from": gov})  # Resets the reporting

    # Check that trigger works if gas costs is less than profitFactor
    profit = 10 ** token.decimals()
    token.transfer(strategy, profit, {"from": gov})
    chain.mine(timedelta=strategy.minReportDelay() + 5)
    assert not strategy.harvestTrigger(profit // strategy.profitFactor())
    assert strategy.harvestTrigger(profit // strategy.profitFactor() - 1)
    strategy.harvest({"from": gov})

    # Check that trigger works if strategy is in debt using debt threshold
    chain.mine(timedelta=strategy.minReportDelay() + 5)
    assert vault.debtOutstanding(strategy) == 0
    vault.revokeStrategy(strategy, {"from": gov})
    assert vault.debtOutstanding(strategy) > strategy.debtThreshold()
    assert strategy.harvestTrigger(MAX_UINT256)

    chain.undo()

    # Check that trigger works if strategy has no outstanding debt but does have a loss
    chain.mine(timedelta=strategy.minReportDelay())
    loss = token.balanceOf(strategy) // 10
    strategy._takeFunds(loss, {"from": gov})
    assert vault.debtOutstanding(strategy) == 0
    assert vault.debtOutstanding(strategy) <= strategy.debtThreshold()
    totalDebt = vault.strategies(strategy).dict()["totalDebt"]
    assert strategy.estimatedTotalAssets() + strategy.debtThreshold() < totalDebt
    assert strategy.harvestTrigger(MAX_UINT256)

    chain.undo()

    # Check that trigger works in emergency exit mode
    strategy.setEmergencyExit({"from": gov})
    assert strategy.harvestTrigger(MAX_UINT256)

    # Stops after it runs out of balance
    while strategy.harvestTrigger(0):
        chain.sleep(1)
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
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})

    # Protected token doesn't work
    with brownie.reverts("!protected"):
        strategy.sweep(strategy.protectedToken(), {"from": gov})

    # But any other random token works
    other_token.transfer(strategy, other_token.balanceOf(gov), {"from": gov})
    assert other_token.address != strategy.want()
    assert other_token.balanceOf(strategy) > 0
    assert other_token.balanceOf(gov) == 0
    # Not any random person can do this
    with brownie.reverts("!authorized"):
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
        with brownie.reverts("Cannot send ether to nonpayable function"):
            # NOTE: gov can do anything
            getattr(strategy, func)(*args, {"from": gov, "value": 1})

    # Fallback fails too
    with brownie.reverts("Cannot send ether to nonpayable function"):
        gov.transfer(strategy, 1)


def test_set_metadataURI(gov, strategy, strategist, rando):
    assert strategy.metadataURI() == ""  # Empty by default
    strategy.setMetadataURI("ipfs://test", {"from": gov})
    assert strategy.metadataURI() == "ipfs://test"
    strategy.setMetadataURI("ipfs://test2", {"from": gov})
    assert strategy.metadataURI() == "ipfs://test2"
    strategy.setMetadataURI("ipfs://test3", {"from": strategist})
    assert strategy.metadataURI() == "ipfs://test3"
    with brownie.reverts("!authorized"):
        strategy.setMetadataURI("ipfs://fake", {"from": rando})


def test_reduce_debt_ratio(strategy, vault, gov, chain):
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["totalDebt"] > 0
    old_debt_ratio = vault.strategies(strategy).dict()["debtRatio"]
    vault.updateStrategyDebtRatio(strategy, old_debt_ratio // 2, {"from": gov})

    assert vault.debtOutstanding(strategy) > 0
