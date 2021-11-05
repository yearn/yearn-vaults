import pytest
import brownie
from brownie import ZERO_ADDRESS

MAX_UINT256 = 2 ** 256 - 1


def test_upgrade(chain, gov, vault, token, create_vault, vault_token):
    vault_balance = token.balanceOf(vault)

    new_vault = create_vault(token, vault_token)
    vault.upgrade(new_vault, {"from": gov})
    assert token.balanceOf(new_vault) == vault_balance
    balanceBefore = token.balanceOf(gov)
    new_vault.withdraw({"from": gov})
    assert token.balanceOf(gov) == vault_balance + balanceBefore
