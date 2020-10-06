import pytest
import brownie


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

    # But any other random token works (and any random person can do this)
    assert other_token.address != strategy.want()
    assert other_token.balanceOf(strategy) > 0
    assert other_token.balanceOf(gov) == 0
    before = other_token.balanceOf(strategy)
    strategy.sweep(other_token, {"from": rando})
    assert other_token.balanceOf(strategy) == 0
    assert other_token.balanceOf(gov) == before
    assert other_token.balanceOf(rando) == 0
