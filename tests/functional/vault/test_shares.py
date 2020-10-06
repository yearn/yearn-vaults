import pytest
import brownie


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Overriding the one in conftest because it has values already
    yield gov.deploy(Vault, token, gov, gov)


def test_deposit_withdraw(gov, vault, token):
    balance = token.balanceOf(gov)
    token.approve(vault, balance, {"from": gov})
    vault.deposit(balance // 2, {"from": gov})

    assert token.balanceOf(vault) == balance // 2
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    # Do it twice to test behavior when it has shares
    vault.deposit(token.balanceOf(gov), {"from": gov})

    assert vault.totalSupply() == token.balanceOf(vault) == balance
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    vault.withdraw(vault.balanceOf(gov) // 2, {"from": gov})

    assert token.balanceOf(vault) == balance // 2
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    # This works because it's *max* shares, and it adjusts by total available
    vault.withdraw(2 * vault.balanceOf(gov), {"from": gov})

    assert vault.totalSupply() == token.balanceOf(vault) == 0
    assert vault.totalDebt() == 0
    assert token.balanceOf(gov) == balance


def test_transfer(accounts, token, vault, fn_isolation):
    a, b = accounts[0:2]
    token.approve(vault, token.balanceOf(a), {"from": a})
    vault.deposit(token.balanceOf(a), {"from": a})

    assert vault.balanceOf(a) == token.balanceOf(vault)
    assert vault.balanceOf(b) == 0

    vault.transfer(b, vault.balanceOf(a), {"from": a})

    assert vault.balanceOf(a) == 0
    assert vault.balanceOf(b) == token.balanceOf(vault)


def test_transferFrom(accounts, token, vault, fn_isolation):
    a, b, c = accounts[0:3]
    token.approve(vault, token.balanceOf(a), {"from": a})
    vault.deposit(token.balanceOf(a), {"from": a})

    # Unapproved can't send
    with brownie.reverts():
        vault.transferFrom(a, b, vault.balanceOf(a) // 2, {"from": c})

    vault.approve(c, vault.balanceOf(a) // 2, {"from": a})
    assert vault.allowance(a, c) == vault.balanceOf(a) // 2

    # Can't send more than what is approved
    with brownie.reverts():
        vault.transferFrom(a, b, vault.balanceOf(a), {"from": c})

    assert vault.balanceOf(a) == token.balanceOf(vault)
    assert vault.balanceOf(b) == 0

    vault.transferFrom(a, b, vault.balanceOf(a) // 2, {"from": c})

    assert vault.balanceOf(a) == token.balanceOf(vault) // 2
    assert vault.balanceOf(b) == token.balanceOf(vault) // 2

    # If approval is unlimited, little bit of a gas savings
    vault.approve(c, 2 ** 256 - 1, {"from": a})
    vault.transferFrom(a, b, vault.balanceOf(a), {"from": c})

    assert vault.balanceOf(a) == 0
    assert vault.balanceOf(b) == token.balanceOf(vault)
