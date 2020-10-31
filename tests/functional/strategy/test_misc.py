import pytest
import brownie


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

    # Special feature, if keeper is 0x0, it's unauthenticated
    strategy.setKeeper(
        "0x0000000000000000000000000000000000000000", {"from": strategist}
    )
    strategy.tend({"from": rando})
    strategy.harvest({"from": rando})


def test_harvest_tend_trigger(gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    assert not strategy.harvestTrigger(0)

    vault.addStrategy(strategy, 10 ** 18, 1000, 50, {"from": gov})

    token.transfer(strategy, 10 ** 8, {"from": gov})
    assert not strategy.harvestTrigger(10 ** 9)
    assert strategy.harvestTrigger(10 ** 6)

    # Get some debt into the strategy
    strategy.harvest({"from": gov})

    vault.revokeStrategy(strategy, {"from": gov})
    assert strategy.harvestTrigger(10 ** 9)  # Gas cost doesn't matter now

    strategy.setEmergencyExit({"from": gov})
    assert strategy.harvestTrigger(10 ** 9)

    # Stops after it runs out of balance
    while strategy.harvestTrigger(0):
        strategy.harvest({"from": gov})

    assert strategy.estimatedTotalAssets() == 0
    assert not strategy.harvestTrigger(0)


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token)


def test_sweep(gov, strategy, rando, token, other_token):
    token.transfer(strategy, token.balanceOf(gov), {"from": gov})
    other_token.transfer(strategy, other_token.balanceOf(gov), {"from": gov})

    # Strategy want token doesn't work
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts():
        strategy.sweep(token, {"from": gov})

    # But any other random token works
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
