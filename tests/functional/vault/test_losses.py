import pytest
import brownie


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(Vault, token, gov, gov, "", "")


@pytest.fixture
def strategy(gov, vault, TestStrategy):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(TestStrategy, vault)


def test_reporting(vault, strategy, gov, token, rando):
    vault.addStrategy(strategy, 1000, 1000, 0, {"from": gov})
    token.approve(vault, 500, {"from": gov})
    vault.deposit(500, {"from": gov})

    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == 500

    # First loss
    strategy._takeFunds(100, {"from": gov})
    strategy.harvest({"from": gov})
    params = vault.strategies(strategy).dict()
    assert params["totalLoss"] == 100
    assert params["totalDebt"] == 400

    # Harder second loss
    strategy._takeFunds(300, {"from": gov})
    strategy.harvest({"from": gov})
    params = vault.strategies(strategy).dict()
    assert params["totalLoss"] == 400
    assert params["totalDebt"] == 100

    # Strike three
    assert token.balanceOf(strategy) == 100
    strategy._takeFunds(100, {"from": gov})
    assert token.balanceOf(strategy) == 0
    strategy.harvest({"from": gov})
    params = vault.strategies(strategy).dict()
    assert params["totalLoss"] == 500
    assert params["totalDebt"] == 0
