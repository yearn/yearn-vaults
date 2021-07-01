import pytest
import brownie
from brownie import ZERO_ADDRESS


def test_router(router, registry, token, vault, vault2, gov):
    token.approve(router, 2000, {"from": gov})

    # revert no vault
    with brownie.reverts():
        router.deposit(token, 1000, {"from": gov})

    registry.newRelease(vault, {"from": gov})
    registry.endorseVault(vault, {"from": gov})
    assert token.balanceOf(vault) == 0
    router.deposit(token, 1000, {"from": gov})
    assert token.balanceOf(vault) == 1000

    # endorse new version
    registry.newRelease(vault2, {"from": gov})
    registry.endorseVault(vault2, {"from": gov})
    assert token.balanceOf(vault2) == 0
    router.deposit(token, 1000, {"from": gov})
    assert token.balanceOf(vault2) == 1000
