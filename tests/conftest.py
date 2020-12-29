from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from brownie import compile_source, Vault

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parents[1] / "ethpm-config.yaml").read_text()
)["version"]


VAULT_SOURCE_CODE = (Path(__file__).parents[1] / "contracts/Vault.vy").read_text()


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
