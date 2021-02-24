import pytest


@pytest.fixture
def create_token(gov, Token):
    def create_token(decimals):
        return Token.deploy(decimals, {"from": gov})

    yield create_token


@pytest.fixture(params=[18, 8])
def create_vault(gov, create_token, patch_vault_version, request):
    def create_vault(token=None, version=None):
        if token is None:
            token = create_token(request.param)
        vault = patch_vault_version(version).deploy({"from": gov})
        vault.initialize(
            token, gov, gov, f"Yearn {token.name()} Vault", f"yv{token.symbol()}", gov
        )
        vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
        assert vault.token() == token
        return vault

    yield create_vault


@pytest.fixture
def registry(gov, Registry):
    yield Registry.deploy({"from": gov})
