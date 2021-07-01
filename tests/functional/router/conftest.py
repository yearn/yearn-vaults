import pytest


@pytest.fixture
def vault(gov, management, token, create_vault):
    vault = create_vault(token, version="0.4.1", governance=gov)
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def vault2(gov, management, token, create_vault):
    vault = create_vault(token=token, governance=gov)
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def router(gov, registry, Router):
    yield gov.deploy(Router, registry)
