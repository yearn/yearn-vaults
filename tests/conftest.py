from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from eth_account import Account
from eth_account.messages import encode_structured_data

from brownie import compile_source, Token, Vault, web3, chain

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parents[1] / "ethpm-config.yaml").read_text()
)["version"]
VAULT_SOURCE_CODE = (Path(__file__).parents[1] / "contracts/Vault.vy").read_text()


def arg_types(args):
    # NOTE: Struct compatibility between Vyper and Solidity
    if len(args) == 1 and "components" in args[0]:
        args = args[0]["components"]

    # NOTE: Need to filter out `name` and `internalType`,
    #       it isn't useful and hurts our comparisions
    return [
        {k: v for k, v in arg.items() if k not in ("internalType", "name")}
        for arg in args
    ]


@pytest.fixture
def check_api_adherrance():
    def test_api_adherrance(Contract, InterfaceAPI):

        for expected_abi in InterfaceAPI.abi:
            methods = [
                abi for abi in Contract.abi if abi["name"] == expected_abi["name"]
            ]
            assert len(methods) > 0  # Has at least one method with this name

            matching_method = False
            for method in methods:
                # Must be always the same type, even if different signature
                assert method["type"] == expected_abi["type"]

                # All similar methods must have the same mutability
                if "stateMutability" in expected_abi:
                    assert method["stateMutability"] == expected_abi["stateMutability"]

                # We'd discovered a match if Inputs/Outputs match
                if (
                    "inputs" not in expected_abi  # No inputs, so don't check
                    or arg_types(method["inputs"]) == arg_types(expected_abi["inputs"])
                ) and (
                    "outputs" not in expected_abi  # No outputs, so don't check
                    or arg_types(method["outputs"])
                    == arg_types(expected_abi["outputs"])
                ):
                    matching_method = True
                    break  # match discovered, we only need one match (of N methods)

            if not matching_method:
                breakpoint()
            assert (
                matching_method
            ), f"No matching methods to {expected_abi} in {methods}"

    return test_api_adherrance


@pytest.fixture
def patch_vault_version():
    # NOTE: Cache this result so as not to trigger a recompile for every version change
    @lru_cache
    def patch_vault_version(version):
        if version is None:
            return Vault
        else:
            source = VAULT_SOURCE_CODE.replace(PACKAGE_VERSION, version)
            return compile_source(source).Vyper

    return patch_vault_version


def chain_id():
    # BUG: ganache-cli provides mismatching chain.id and chainid()
    # https://github.com/trufflesuite/ganache/issues/1643
    return 1 if web3.clientVersion.startswith("EthereumJS") else chain.id


@pytest.fixture
def sign_token_permit():
    def sign_token_permit(
        token: Token,
        owner: Account,  # NOTE: Must be a eth_key account, not Brownie
        spender: str,
        allowance: int = 2 ** 256 - 1,  # Allowance to set with `permit`
        deadline: int = 0,  # 0 means no time limit
        override_nonce: int = None,
    ):
        if override_nonce:
            nonce = override_nonce
        else:
            nonce = token.nonces(owner.address)
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
                    {"name": "value", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "domain": {
                "name": token.name(),
                "version": "1",
                "chainId": chain_id(),
                "verifyingContract": str(token),
            },
            "primaryType": "Permit",
            "message": {
                "owner": owner.address,
                "spender": spender,
                "value": allowance,
                "nonce": nonce,
                "deadline": deadline,
            },
        }
        permit = encode_structured_data(data)
        return owner.sign_message(permit)

    return sign_token_permit


@pytest.fixture
def sign_vault_permit():
    def sign_vault_permit(
        vault: Vault,
        owner: Account,  # NOTE: Must be a eth_key account, not Brownie
        spender: str,
        allowance: int = 2 ** 256 - 1,  # Allowance to set with `permit`
        deadline: int = 0,  # 0 means no time limit
        override_nonce: int = None,
    ):
        name = "Yearn Vault"
        version = vault.apiVersion()
        if override_nonce:
            nonce = override_nonce
        else:
            nonce = vault.nonces(owner.address)
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
                    {"name": "value", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "domain": {
                "name": name,
                "version": version,
                "chainId": chain_id(),
                "verifyingContract": str(vault),
            },
            "primaryType": "Permit",
            "message": {
                "owner": owner.address,
                "spender": spender,
                "value": allowance,
                "nonce": nonce,
                "deadline": deadline,
            },
        }
        permit = encode_structured_data(data)
        return owner.sign_message(permit).signature

    return sign_vault_permit


# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass
