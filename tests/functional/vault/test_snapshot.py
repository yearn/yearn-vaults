import pytest


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Overriding the one in conftest because it has values already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    yield vault


def test_deposit_transfer_withdraw(chain, gov, vault, token, rando):
    starting_block = len(chain) - 1

    balance = token.balanceOf(gov)
    token.approve(vault, balance, {"from": gov})
    vault.deposit(balance // 2, {"from": gov})
    bal = vault.balanceOf(gov)

    assert vault.balanceOfAt(gov, starting_block) == 0
    assert vault.balanceOfAt(gov, starting_block + 2) == bal

    # Do it twice to test behavior when it has shares
    vault.deposit({"from": gov})
    assert vault.balanceOfAt(gov, starting_block + 2) == bal
    bal = vault.balanceOf(gov)
    assert vault.balanceOfAt(gov, starting_block + 3) == bal
    assert vault.totalSupplyAt(starting_block + 3) == bal

    vault.transfer(rando, bal // 2, {"from": gov})
    assert vault.balanceOfAt(gov, starting_block + 3) == bal
    bal = vault.balanceOf(gov)
    bal2 = vault.balanceOf(rando)
    assert vault.balanceOfAt(gov, starting_block + 4) == bal
    assert vault.balanceOfAt(rando, starting_block + 3) == 0
    assert vault.balanceOfAt(rando, starting_block + 4) == bal2

    vault.withdraw({"from": gov})
    vault.withdraw({"from": rando})

    assert vault.balanceOfAt(gov, starting_block + 6) == 0
    assert vault.balanceOfAt(rando, starting_block + 6) == 0
    assert vault.totalSupplyAt(starting_block + 5) == bal2
    assert vault.totalSupplyAt(starting_block + 6) == 0
