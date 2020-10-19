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


def test_addStrategy(web3, gov, vault, strategy, rando):

    # Only governance can add a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 1000, 10, 50, {"from": rando})

    assert vault.strategies(strategy) == [0, 0, 0, 0, 0, 0, 0]

    vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})
    assert vault.strategies(strategy) == [
        50,
        web3.eth.blockNumber,
        1000,
        10,
        web3.eth.blockNumber,
        0,
        0,
    ]
    assert vault.withdrawalQueue(0) == strategy

    # Can't add a strategy twice
    with brownie.reverts():
        vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})


def test_updateStrategy(web3, gov, vault, strategy, rando):
    # Can't update an unapproved strategy
    with brownie.reverts():
        vault.updateStrategyDebtLimit(strategy, 1500, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyRateLimit(strategy, 15, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})

    vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})
    activation_block = web3.eth.blockNumber  # Deployed right before test started

    # Not just anyone can update a strategy
    with brownie.reverts():
        vault.updateStrategyDebtLimit(strategy, 1500, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyRateLimit(strategy, 15, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": rando})

    vault.updateStrategyDebtLimit(strategy, 1500, {"from": gov})
    assert vault.strategies(strategy) == [
        50,
        activation_block,
        1500,  # This changed
        10,
        activation_block,
        0,
        0,
    ]

    vault.updateStrategyRateLimit(strategy, 15, {"from": gov})
    assert vault.strategies(strategy) == [
        50,
        activation_block,
        1500,
        15,  # This changed
        activation_block,
        0,
        0,
    ]

    vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})
    assert vault.strategies(strategy) == [
        75,  # This changed
        activation_block,
        1500,
        15,
        activation_block,
        0,
        0,
    ]


def test_migrateStrategy(gov, vault, strategy, rando, TestStrategy):
    vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})

    # Not just anyone can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, rando, {"from": rando})

    # Can't migrate to itself
    with brownie.reverts():
        vault.migrateStrategy(strategy, strategy, {"from": gov})

    # Migrating not in the withdrawal queue (for coverage)
    vault.removeStrategyFromQueue(strategy, {"from": gov})
    new_strategy = gov.deploy(TestStrategy, vault)
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # Can migrate back again (but it starts out fresh)
    vault.migrateStrategy(new_strategy, strategy, {"from": gov})

    # Can't migrate an unapproved strategy
    with brownie.reverts():
        vault.migrateStrategy(new_strategy, strategy, {"from": gov})

    # Can't migrate to an already approved strategy
    approved_strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(approved_strategy, 1000, 10, 50, {"from": gov})
    with brownie.reverts():
        vault.migrateStrategy(strategy, approved_strategy, {"from": gov})


def test_revokeStrategy(web3, gov, vault, strategy, rando):
    vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})
    activation_block = web3.eth.blockNumber  # Deployed right before test started

    # Not just anyone can revoke a strategy
    with brownie.reverts():
        vault.revokeStrategy(strategy, {"from": rando})

    vault.revokeStrategy(strategy, {"from": gov})
    assert vault.strategies(strategy) == [
        50,
        activation_block,
        0,  # This changed
        10,
        activation_block,
        0,
        0,
    ]

    assert vault.withdrawalQueue(0) == strategy
    vault.removeStrategyFromQueue(strategy, {"from": gov})
    assert vault.withdrawalQueue(0) == "0x0000000000000000000000000000000000000000"
    # Can only do it once
    with brownie.reverts():
        vault.removeStrategyFromQueue(strategy, {"from": gov})


def test_ordering(gov, vault, TestStrategy, rando):
    # Show that a lot of strategies get properly ordered
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(19)]
    [vault.addStrategy(s, 1000, 10, 50, {"from": gov}) for s in strategies]

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # Show that strategies can be reordered
    strategies = list(reversed(strategies))
    # NOTE: Not just anyone can do this
    with brownie.reverts():
        vault.setWithdrawalQueue(
            strategies
            + ["0x0000000000000000000000000000000000000000"] * (20 - len(strategies)),
            {"from": rando},
        )
    vault.setWithdrawalQueue(
        strategies
        + ["0x0000000000000000000000000000000000000000"] * (20 - len(strategies)),
        {"from": gov},
    )

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # Show that adding a new one properly orders
    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})
    strategies.append(strategy)

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # NOTE: limited to only a certain amount of strategies
    with brownie.reverts():
        vault.addStrategy(gov.deploy(TestStrategy, vault), 1000, 10, 50, {"from": gov})

    # Show that removing from the middle properly orders
    strategy = strategies.pop(1)
    # NOTE: Not just anyone can do this
    with brownie.reverts():
        vault.removeStrategyFromQueue(strategy, {"from": rando})
    vault.removeStrategyFromQueue(strategy, {"from": gov})

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy


def test_reporting(vault, strategy, gov, rando):
    # Not just anyone can call `Vault.report()`
    with brownie.reverts():
        vault.report(0, {"from": rando})

    strategy.tend({"from": gov})  # Do this for converage of `Strategy.tend()`

    vault.addStrategy(strategy, 1000, 10, 50, {"from": gov})
    vault.expectedReturn(strategy)  # Do this for coverage of `Vault._expectedReturn()`
