import brownie
import pytest

from eth_account import Account

AMOUNT = 100


@pytest.mark.parametrize("expires", [True, False])
def test_permit(chain, rando, vault, sign_vault_permit, expires):
    owner = Account.create()
    deadline = chain[-1].timestamp + 3600 if expires else 0
    signature = sign_vault_permit(
        vault, owner, str(rando), allowance=AMOUNT, deadline=deadline
    )
    assert vault.allowance(owner.address, rando) == 0
    vault.permit(owner.address, rando, AMOUNT, deadline, signature, {"from": rando})
    assert vault.allowance(owner.address, rando) == AMOUNT


def test_permit_wrong_signature(rando, vault, sign_vault_permit):
    owner = Account.create()
    # NOTE: Default `allowance` is unlimited, not `AMOUNT`
    signature = sign_vault_permit(vault, owner, str(rando))
    assert vault.allowance(owner.address, rando) == 0
    with brownie.reverts("dev: invalid signature"):
        # Fails because wrong `allowance` value provided
        vault.permit(owner.address, rando, AMOUNT, 0, signature, {"from": rando})


def test_permit_expired(chain, rando, vault, sign_vault_permit):
    owner = Account.create()
    deadline = chain[-1].timestamp - 600
    # NOTE: Default `deadline` is 0, not a timestamp in the past
    signature = sign_vault_permit(vault, owner, str(rando), allowance=AMOUNT)
    assert vault.allowance(owner.address, rando) == 0
    with brownie.reverts("dev: permit expired"):
        # Fails because wrong `deadline` timestamp provided (it expired)
        vault.permit(owner.address, rando, AMOUNT, deadline, signature, {"from": rando})


def test_permit_bad_owner(rando, vault, sign_vault_permit):
    owner = Account.create()
    signature = sign_vault_permit(vault, owner, str(rando), allowance=AMOUNT)
    assert vault.allowance(owner.address, owner.address) == 0
    with brownie.reverts("dev: invalid owner"):
        # Fails because wrong `owner` provided
        vault.permit(brownie.ZERO_ADDRESS, rando, AMOUNT, 0, signature, {"from": rando})
