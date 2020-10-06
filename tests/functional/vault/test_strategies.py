import pytest
import brownie


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(Vault, token, gov, gov)


@pytest.fixture
def strategy(gov, vault, TestStrategy):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(TestStrategy, vault, gov)


def test_addStrategy(web3, gov, vault, strategy, rando):

    # Only governance can add a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 1000, 10, {"from": rando})

    assert vault.strategies(strategy) == [0, 0, 0, 0, 0, 0]

    vault.addStrategy(strategy, 1000, 10, {"from": gov})
    assert vault.strategies(strategy) == [
        web3.eth.blockNumber,
        1000,
        10,
        web3.eth.blockNumber,
        0,
        0,
    ]


def test_updateStrategy(web3, gov, vault, strategy, rando):
    # Can't update an unapproved strategy
    with brownie.reverts():
        vault.updateStrategy(strategy, 1500, 15, {"from": gov})

    vault.addStrategy(strategy, 1000, 10, {"from": gov})
    activation_block = web3.eth.blockNumber  # Deployed right before test started

    # Not just anyone can update a strategy
    with brownie.reverts():
        vault.updateStrategy(strategy, 1500, 15, {"from": rando})

    vault.updateStrategy(strategy, 1500, 15, {"from": gov})
    assert vault.strategies(strategy) == [
        activation_block,
        1500,  # This changed
        15,  # This changed
        activation_block,
        0,
        0,
    ]


def test_migrateStrategy(accounts, gov, vault, rando):
    strategy = accounts[2]
    vault.addStrategy(strategy, 1000, 10, {"from": gov})

    # Not just anyone can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, {"from": rando})

    # Can't migrate to itself
    with brownie.reverts():
        vault.migrateStrategy(strategy, {"from": strategy})


def test_revokeStrategy(web3, gov, vault, strategy, rando):
    vault.addStrategy(strategy, 1000, 10, {"from": gov})
    activation_block = web3.eth.blockNumber  # Deployed right before test started

    # Not just anyone can revoke a strategy
    with brownie.reverts():
        vault.revokeStrategy(strategy, {"from": rando})

    vault.revokeStrategy(strategy, {"from": gov})
    assert vault.strategies(strategy) == [
        activation_block,
        0,  # This changed
        10,
        activation_block,
        0,
        0,
    ]


def test_sync(vault, strategy, gov, rando):
    # Not just anyone can call sync()
    with brownie.reverts():
        vault.sync(0, {"from": rando})

    strategy.tend({"from": gov})  # Do this for converage of Strategy.tend()

    vault.addStrategy(strategy, 1000, 10, {"from": gov})
    vault.expectedReturn(strategy)  # Do this for coverage of Vault._expectedReturn()
