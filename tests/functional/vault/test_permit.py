from brownie import chain
from eth_account import Account
from eth_account._utils.structured_data.hashing import hash_domain
from eth_account.messages import encode_structured_data
from eth_utils import encode_hex


def test_permit(vault):
    owner = Account.create()
    spender = Account.create()
    nonce = vault.nonces(owner.address)
    expiry = chain[-1].timestamp + 3600
    amount = 10 ** 21
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
            "name": "Yearn Vault",
            "version": vault.apiVersion(),
            "chainId": 1,
            "verifyingContract": str(vault),
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
    assert encode_hex(hash_domain(data)) == vault.DOMAIN_SEPARATOR()
    message = encode_structured_data(data)
    signed = owner.sign_message(message)
    assert vault.allowance(owner.address, spender.address) == 0
    vault.permit(owner.address, spender.address, amount, expiry, signed.signature)
    assert vault.allowance(owner.address, spender.address) == amount
