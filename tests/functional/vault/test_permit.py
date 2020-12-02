import brownie
import pytest
from brownie import chain
from eth_account import Account
from eth_account.messages import encode_structured_data

amount = 100
owner = Account.create()
spender = Account.create()


def generate_permit(vault, owner: Account, spender: Account, amount, nonce, expiry):
    name = "Yearn Vault"
    version = vault.apiVersion()
    chain_id = 1  # ganache bug https://github.com/trufflesuite/ganache/issues/1643
    contract = str(vault)
    data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Permit": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "expiry", "type": "uint256"},
            ],
        },
        "domain": {
            "name": name,
            "version": version,
            "chainId": chain_id,
            "verifyingContract": contract,
        },
        "primaryType": "Permit",
        "message": {
            "owner": owner.address,
            "spender": spender.address,
            "amount": amount,
            "nonce": nonce,
            "expiry": expiry,
        },
    }
    return encode_structured_data(data)


@pytest.mark.parametrize("expiry", [True, False])
def test_permit(vault, expiry):
    nonce = vault.nonces(owner.address)
    expiry = chain[-1].timestamp + 3600 if expiry else 0
    permit = generate_permit(vault, owner, spender, amount, nonce, expiry)
    signature = owner.sign_message(permit).signature
    assert vault.allowance(owner.address, spender.address) == 0
    vault.permit(owner.address, spender.address, amount, expiry, signature)
    assert vault.allowance(owner.address, spender.address) == amount


def test_permit_wrong_signature(vault):
    nonce = vault.nonces(owner.address)
    expiry = 0
    permit = generate_permit(vault, owner, spender, amount, nonce, expiry)
    signature = spender.sign_message(permit).signature
    assert vault.allowance(owner.address, spender.address) == 0
    with brownie.reverts("dev: invalid signature"):
        vault.permit(owner.address, spender.address, amount, expiry, signature)


def test_permit_expired(vault):
    nonce = vault.nonces(owner.address)
    expiry = chain[-1].timestamp - 600
    permit = generate_permit(vault, owner, spender, amount, nonce, expiry)
    signature = owner.sign_message(permit).signature
    assert vault.allowance(owner.address, spender.address) == 0
    with brownie.reverts("dev: permit expired"):
        vault.permit(owner.address, spender.address, amount, expiry, signature)
