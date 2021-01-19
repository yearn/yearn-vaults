from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from brownie import compile_source, Vault

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


# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass
