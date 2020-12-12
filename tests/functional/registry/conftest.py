from pathlib import Path
import difflib

import pytest
import yaml

from brownie import compile_source

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parents[3] / "ethpm-config.yaml").read_text()
)["version"]


VAULT_SOURCE_CODE = (Path(__file__).parents[3] / "contracts/Vault.vy").read_text()


def patch_vault_version(version):
    source = VAULT_SOURCE_CODE.replace(PACKAGE_VERSION, version)
    [print(li) for li in difflib.ndiff(VAULT_SOURCE_CODE, source) if li[0] != " "]
    return compile_source(source).Vyper


@pytest.fixture
def create_token(gov, Token):
    def create_token():
        return Token.deploy({"from": gov})

    yield create_token


@pytest.fixture
def create_vault(gov, create_token):
    def create_vault(token=None, version=PACKAGE_VERSION):
        if token is None:
            token = create_token()
        vault = patch_vault_version(version).deploy({"from": gov})
        vault.initialize(
            token, gov, gov, f"Yearn {token.name()} Vault", f"yv{token.symbol()}", gov
        )
        assert vault.token() == token
        return vault

    yield create_vault


@pytest.fixture
def registry(gov, Registry):
    yield Registry.deploy({"from": gov})
