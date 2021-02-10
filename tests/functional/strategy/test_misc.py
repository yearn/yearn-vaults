import pytest
import brownie

MAX_UINT256 = 2 ** 256 - 1


def test_harvest_tend_authority(gov, keeper, strategist, strategy, rando):
    # Only keeper, strategist, or gov can call tend
    strategy.tend({"from": keeper})
    strategy.tend({"from": strategist})
    strategy.tend({"from": gov})
    with brownie.reverts():
        strategy.tend({"from": rando})

    # Only keeper, strategist, or gov can call harvest
    strategy.harvest({"from": keeper})
    strategy.harvest({"from": strategist})
    strategy.harvest({"from": gov})
    with brownie.reverts():
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
    profit = 10 ** 8
    token.transfer(strategy, profit, {"from": gov})
    chain.mine(timedelta=strategy.minReportDelay())
    assert not strategy.harvestTrigger(profit // strategy.profitFactor())
    assert strategy.harvestTrigger(profit // strategy.profitFactor() - 1)
    strategy.harvest({"from": gov})

    # Check that trigger works if strategy is in debt using debt threshold
    chain.mine(timedelta=strategy.minReportDelay())
    assert vault.debtOutstanding(strategy) == 0
    vault.revokeStrategy(strategy, {"from": gov})
    assert vault.debtOutstanding(strategy) > strategy.debtThreshold()
    assert strategy.harvestTrigger(MAX_UINT256)

    chain.undo()

    # Check that trigger works in emergency exit mode
    strategy.setEmergencyExit({"from": gov})
    assert strategy.harvestTrigger(MAX_UINT256)

    # Stops after it runs out of balance
    while strategy.harvestTrigger(0):
        strategy.harvest({"from": gov})

    assert strategy.estimatedTotalAssets() == 0


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token)


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
        with brownie.reverts("Cannot send ether to nonpayable function"):
            # NOTE: gov can do anything
            getattr(strategy, func)(*args, {"from": gov, "value": 1})

    # Fallback fails too
    with brownie.reverts("Cannot send ether to nonpayable function"):
        gov.transfer(strategy, 1)


def test_set_metadataURI(gov, strategy, rando):
    assert strategy.metadataURI() == ""  # Empty by default
    strategy.setMetadataURI("ipfs://test", {"from": gov})
    assert strategy.metadataURI() == "ipfs://test"
    strategy.setMetadataURI("ipfs://test2", {"from": gov})
    assert strategy.metadataURI() == "ipfs://test2"
    with brownie.reverts():
        strategy.setMetadataURI("ipfs://fake", {"from": rando})


def test_sandwich_attack(
    chain, TestStrategy, web3, token, gov, vault, strategist, rando
):

    honest_lp = gov
    attacker = rando
    balance = token.balanceOf(honest_lp) / 2

    # seed attacker their funds
    token.transfer(attacker, balance, {"from": honest_lp})

    # we don't use the one in conftest because we want no rate limit
    strategy = strategist.deploy(TestStrategy, vault)
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.addStrategy(strategy, 4_000, 0, 2 ** 256 - 1, 0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})

    strategy.harvest({"from": strategist})
    # strategy is returning 0.02%. Equivalent to 35.6% a year at 5 harvests a day
    profit_to_be_returned = token.balanceOf(strategy) / 5000
    token.transfer(strategy, profit_to_be_returned, {"from": honest_lp})

    # now for the attack

    # attacker sees harvest enter tx pool
    attack_amount = balance

    print(f"Attack Capital: {attack_amount}")

    # attacker deposits
    token.approve(vault, attack_amount, {"from": attacker})
    vault.deposit(attack_amount, {"from": attacker})

    # harvest happens
    strategy.harvest({"from": strategist})

    chain.sleep(1)
    chain.mine(1)

    # attacker withdraws. Pays back loan. and keeps or sells profit
    vault.withdraw(vault.balanceOf(attacker), {"from": attacker})

    profit = token.balanceOf(attacker) - attack_amount
    print(f"Attack Profit: {profit}")
    profit_percent = profit / attack_amount

    print(f"Attack Profit Percent: {profit_percent}")
    # 5 rebases a day = 1780 a year. Less than 0.0004% profit on attack makes it closer to neutral EV
    assert profit_percent < 0.000004
