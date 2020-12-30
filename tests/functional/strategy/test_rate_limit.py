import pytest
import brownie


def test_simple_limit(chain, gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    # NOTE: 20 % of Vault assets is 2_000 BPS
    vault.addStrategy(strategy, 2_000, 10, 0, {"from": gov})

    # Mine a block in a second
    start = chain.time()
    chain.mine(1, start + 1)

    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    # Doing this because even if set the time of the block
    # the clock keeps ticking while the code runs.
    # a balance of 20 would mean that it took more than 2 secs
    # to harvest
    assert token.balanceOf(strategy) < 20

    # After a while the strategy will be able to get up to debtLimit
    chain.mine(1, start + 1000)
    strategy.harvest({"from": gov})
    # Doing this because even if set the time of the block
    # the clock keeps ticking while the code runs.
    # a balance of 10020 would mean that it took more than 2 secs
    # to harvest
    assert token.balanceOf(strategy) < 10020


def test_zero_limit(gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    # NOTE: 20 % of Vault assets is 2_000 BPS
    vault.addStrategy(strategy, 2_000, 0, 0, {"from": gov})

    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == vault.totalAssets() // 5
