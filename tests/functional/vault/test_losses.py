import pytest
import brownie

DAY = 86400  # seconds


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Because the fixture has tokens in it already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    yield vault


@pytest.fixture
def strategy(gov, vault, TestStrategy):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(TestStrategy, vault)


def test_losses(chain, vault, strategy, gov, token):
    vault.addStrategy(strategy, 1000, 1000, 0, {"from": gov})
    token.approve(vault, 500, {"from": gov})
    vault.deposit(500, {"from": gov})

    chain.sleep(DAY // 10)
    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == 500

    # First loss
    chain.sleep(DAY // 10)
    strategy._takeFunds(100, {"from": gov})
    strategy.harvest({"from": gov})
    params = vault.strategies(strategy).dict()
    assert params["totalLoss"] == 100
    assert params["totalDebt"] == 400

    # Harder second loss
    chain.sleep(DAY // 10)
    strategy._takeFunds(300, {"from": gov})
    strategy.harvest({"from": gov})
    params = vault.strategies(strategy).dict()
    assert params["totalLoss"] == 400
    assert params["totalDebt"] == 100

    # Strike three
    chain.sleep(DAY // 10)
    assert token.balanceOf(strategy) == 100
    strategy._takeFunds(100, {"from": gov})
    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    params = vault.strategies(strategy).dict()
    assert params["totalLoss"] == 500
    assert params["totalDebt"] == 0
