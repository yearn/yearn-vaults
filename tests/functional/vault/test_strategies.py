import pytest
import brownie


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture
def vault(gov, management, token, Vault):
    # NOTE: Because the fixture has tokens in it already
    vault = gov.deploy(Vault, token, gov, gov, "", "")
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def strategy(gov, vault, TestStrategy):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(TestStrategy, vault)


@pytest.fixture
def other_strategy(gov, vault, TestStrategy):
    yield gov.deploy(TestStrategy, vault)


@pytest.fixture
def wrong_strategy(gov, Vault, Token, TestStrategy):
    otherToken = gov.deploy(Token)
    otherVault = gov.deploy(Vault, otherToken, gov, gov, "", "")
    yield gov.deploy(TestStrategy, otherVault)


def test_addStrategy(chain, gov, vault, strategy, wrong_strategy, rando):

    # Only governance can add a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 10000, 10, 1000, {"from": rando})

    assert vault.strategies(strategy).dict() == {
        "performanceFee": 0,
        "activation": 0,
        "debtLimit": 0,
        "rateLimit": 0,
        "lastReport": 0,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtLimit": 10000,
        "rateLimit": 10,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }
    assert vault.withdrawalQueue(0) == strategy

    # Can't add a strategy twice
    with brownie.reverts():
        vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})

    # Can't add a strategy with incorrect vault or want token
    with brownie.reverts():
        vault.addStrategy(wrong_strategy, 10000, 10, 1000, {"from": gov})


def test_updateStrategy(chain, gov, vault, strategy, rando):
    # Can't update an unapproved strategy
    with brownie.reverts():
        vault.updateStrategyDebtLimit(strategy, 15000, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyRateLimit(strategy, 15, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})

    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]

    # Not just anyone can update a strategy
    with brownie.reverts():
        vault.updateStrategyDebtLimit(strategy, 15000, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyRateLimit(strategy, 15, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": rando})

    vault.updateStrategyDebtLimit(strategy, 15000, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtLimit": 15000,  # This changed
        "rateLimit": 10,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.updateStrategyRateLimit(strategy, 15, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtLimit": 15000,
        "rateLimit": 15,  # This changed
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 75,  # This changed
        "activation": activation_timestamp,
        "debtLimit": 15000,
        "rateLimit": 15,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }


def test_migrateStrategy(gov, vault, strategy, rando, TestStrategy):
    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})

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
    vault.addStrategy(approved_strategy, 10000, 10, 1000, {"from": gov})
    with brownie.reverts():
        vault.migrateStrategy(strategy, approved_strategy, {"from": gov})


def test_revokeStrategy(chain, gov, vault, strategy, rando):
    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]

    # Not just anyone can revoke a strategy
    with brownie.reverts():
        vault.revokeStrategy(strategy, {"from": rando})

    vault.revokeStrategy(strategy, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtLimit": 0,  # This changed
        "rateLimit": 10,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    assert vault.withdrawalQueue(0) == strategy
    vault.removeStrategyFromQueue(strategy, {"from": gov})
    assert vault.withdrawalQueue(0) == ZERO_ADDRESS
    # Can only do it once
    with brownie.reverts():
        vault.removeStrategyFromQueue(strategy, {"from": gov})


def test_ordering(gov, vault, TestStrategy, rando):
    # Show that a lot of strategies get properly ordered
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(19)]

    # Can't add un-approved strategies
    with brownie.reverts():
        vault.setWithdrawalQueue(
            strategies + [ZERO_ADDRESS] * (20 - len(strategies)), {"from": gov},
        )

    [vault.addStrategy(s, 10000, 10, 1000, {"from": gov}) for s in strategies]

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # Show that strategies can be reordered
    strategies = list(reversed(strategies))
    # NOTE: Not just anyone can do this
    with brownie.reverts():
        vault.setWithdrawalQueue(
            strategies + [ZERO_ADDRESS] * (20 - len(strategies)), {"from": rando},
        )
    vault.setWithdrawalQueue(
        strategies + [ZERO_ADDRESS] * (20 - len(strategies)), {"from": gov},
    )

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # Show that adding a new one properly orders
    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})
    strategies.append(strategy)

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # NOTE: limited to only a certain amount of strategies
    with brownie.reverts():
        vault.addStrategy(
            gov.deploy(TestStrategy, vault), 10000, 10, 1000, {"from": gov}
        )

    # Show that removing from the middle properly orders
    removed_strategy = strategies.pop(1)
    # NOTE: Not just anyone can do this
    with brownie.reverts():
        vault.removeStrategyFromQueue(removed_strategy, {"from": rando})

    vault.removeStrategyFromQueue(removed_strategy, {"from": gov})

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    assert vault.withdrawalQueue(len(strategies)) == ZERO_ADDRESS

    # Not just anyone can add it back
    with brownie.reverts():
        vault.addStrategyToQueue(removed_strategy, {"from": rando})

    # Can't add an unauthorized strategy
    with brownie.reverts():
        vault.addStrategyToQueue(rando, {"from": gov})

    vault.addStrategyToQueue(removed_strategy, {"from": gov})
    strategies.append(removed_strategy)

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # Can't add the same strategy twice
    with brownie.reverts():
        vault.addStrategyToQueue(removed_strategy, {"from": gov})


def test_reporting(vault, strategy, gov, rando):
    # Not just anyone can call `Vault.report()`
    with brownie.reverts():
        vault.report(0, 0, 0, {"from": rando})

    strategy.tend({"from": gov})  # Do this for converage of `Strategy.tend()`

    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})
    vault.expectedReturn(strategy)  # Do this for coverage of `Vault._expectedReturn()`


def test_strategy_limits(gov, management, vault, strategy):
    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})

    vault.updateStrategyDebtLimit(strategy, 50, {"from": management})
    assert vault.strategies(strategy).dict()["debtLimit"] == 50

    vault.updateStrategyRateLimit(strategy, 20, {"from": management})
    assert vault.strategies(strategy).dict()["rateLimit"] == 20


def test_management_permission(management, vault, strategy, other_strategy):

    with brownie.reverts():
        vault.addStrategy(strategy, 10000, 10, 1000, {"from": management})

    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 10, {"from": management})

    with brownie.reverts():
        vault.migrateStrategy(strategy, other_strategy, {"from": management})

    with brownie.reverts():
        vault.setDepositLimit(10, {"from": management})


@pytest.fixture
def test_withdrawalQueue(gov, management, vault, strategy, other_strategy):
    vault.addStrategy(strategy, 10000, 10, 1000, {"from": gov})
    vault.addStrategy(other_strategy, 10000, 10, 1000, {"from": gov})

    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == other_strategy

    queue = [ZERO_ADDRESS] * 20
    queue[0] = other_strategy
    queue[1] = strategy
    vault.setWithdrawalQueue(queue, {"from": management})

    assert vault.withdrawalQueue(1) == strategy
    assert vault.withdrawalQueue(0) == other_strategy

    vault.removeStrategyFromQueue(other_strategy, {"from": management})
    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == ZERO_ADDRESS

    vault.addStrategyToQueue(other_strategy, {"from": management})
    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == other_strategy
