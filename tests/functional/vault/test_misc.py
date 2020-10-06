import pytest
import brownie


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token)


def test_sweep(gov, vault, rando, token, other_token):
    token.transfer(vault, token.balanceOf(gov), {"from": gov})
    other_token.transfer(vault, other_token.balanceOf(gov), {"from": gov})

    # Vault wrapped token doesn't work
    assert token.address == vault.token()
    assert token.balanceOf(vault) > 0
    with brownie.reverts():
        vault.sweep(token, {"from": gov})

    # But any other random token works (and any random person can do this)
    assert other_token.address != vault.token()
    assert other_token.balanceOf(vault) > 0
    assert other_token.balanceOf(gov) == 0
    before = other_token.balanceOf(vault)
    vault.sweep(other_token, {"from": rando})
    assert other_token.balanceOf(vault) == 0
    assert other_token.balanceOf(gov) == before
    assert other_token.balanceOf(rando) == 0
