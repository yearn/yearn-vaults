import pytest
import brownie


def test_simple_limit(chain, gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    # NOTE: 20 % of Vault assets is 2_000 BPS
    vault.addStrategy(strategy, 2_000, 10, 0, {"from": gov})

    # Mine a block in a second
    chain.mine(timedelta=1)

    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    # Doing this because even if set the time of the block
    # the clock keeps ticking while the code runs.
    # a balance of 30 would mean that it took more than 1 secs
    # to harvest (+1 for the timedelta, and potentially +1 for rollover)
    assert token.balanceOf(strategy) < 30

    # After a while the strategy will be able to get up to debtLimit
    chain.mine(timedelta=1000)
    strategy.harvest({"from": gov})
    # Doing this because even if set the time of the block
    # the clock keeps ticking while the code runs.
    # a balance of 10030 would mean that it took more than 1 secs
    # to harvest (+1 for the timedelta, and potentially +1 for rollover)
    assert token.balanceOf(strategy) < 10030


def test_zero_limit(gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    # NOTE: 20 % of Vault assets is 2_000 BPS
    vault.addStrategy(strategy, 2_000, 0, 0, {"from": gov})

    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == vault.totalAssets() // 5
