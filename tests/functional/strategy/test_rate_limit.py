import pytest
import brownie


def test_simple_limit(chain, gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 1000, 10, 0, {"from": gov})

    token.approve(vault, 5000, {"from": gov})
    vault.deposit(5000, {"from": gov})

    # Mine a block in a second
    start = chain.time()
    chain.mine(1, start + 1)

    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    # Doing this because even if set the time of the block
    # the clock keeps ticking while the code runs.
    # a balance of 40 would mean that it took more than 4 secs
    # to harvest
    assert token.balanceOf(strategy) <= 40

    # After a while the strategy will be able to get up to debtLimit
    chain.mine(1, start + 1000)
    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == 1000


def test_zero_limit(chain, gov, vault, token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 1000, 0, 0, {"from": gov})

    token.approve(vault, 5000, {"from": gov})
    vault.deposit(5000, {"from": gov})

    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == 1000
