import pytest
import brownie


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture
def vault(gov, management, token, Vault):
    # NOTE: Because the fixture has tokens in it already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def strategy(gov, vault, TestStrategy):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(TestStrategy, vault)


@pytest.fixture
def other_strategy(gov, vault, TestStrategy):
    # NOTE: Because the fixture has tokens in it already
    yield gov.deploy(TestStrategy, vault)


@pytest.fixture
def wrong_strategy(gov, Vault, Token, TestStrategy):
    otherToken = gov.deploy(Token)
    otherVault = gov.deploy(Vault)
    otherVault.initialize(
        otherToken,
        gov,
        gov,
        otherToken.symbol() + " yVault",
        "yv" + otherToken.symbol(),
        gov,
    )
    otherVault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    yield gov.deploy(TestStrategy, otherVault)


def test_addStrategy(
    chain, gov, vault, strategy, other_strategy, wrong_strategy, rando
):

    # Only governance can add a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": rando})

    assert vault.strategies(strategy).dict() == {
        "performanceFee": 0,
        "activation": 0,
        "debtRatio": 0,
        "minDebtIncrease": 0,
        "maxDebtIncrease": 0,
        "lastReport": 0,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 100,
        "minDebtIncrease": 10,
        "maxDebtIncrease": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }
    assert vault.withdrawalQueue(0) == strategy

    # Can't add a strategy twice
    with brownie.reverts():
        vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})

    # Can't add a strategy with incorrect vault or want token
    with brownie.reverts():
        vault.addStrategy(wrong_strategy, 100, 10, 20, 1000, {"from": gov})

    # Can't add a strategy with a debt ratio more than the maximum
    leftover_ratio = 10_000 - vault.debtRatio()
    with brownie.reverts():
        vault.addStrategy(
            other_strategy, leftover_ratio + 1, 10, 20, 1000, {"from": gov}
        )

    vault.addStrategy(other_strategy, leftover_ratio, 10, 20, 1000, {"from": gov})
    assert vault.debtRatio() == 10_000


def test_updateStrategy(chain, gov, vault, strategy, rando):
    # Can't update an unapproved strategy
    with brownie.reverts():
        vault.updateStrategyDebtRatio(strategy, 500, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyMinDebtIncrease(strategy, 15, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyMaxDebtIncrease(strategy, 15, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})

    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]

    # Not just anyone can update a strategy
    with brownie.reverts():
        vault.updateStrategyDebtRatio(strategy, 500, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyMinDebtIncrease(strategy, 15, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyMaxDebtIncrease(strategy, 15, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": rando})

    vault.updateStrategyDebtRatio(strategy, 500, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 500,  # This changed
        "minDebtIncrease": 10,
        "maxDebtIncrease": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.updateStrategyMinDebtIncrease(strategy, 15, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 500,
        "minDebtIncrease": 15,  # This changed
        "maxDebtIncrease": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.updateStrategyMaxDebtIncrease(strategy, 15, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 500,
        "minDebtIncrease": 15,
        "maxDebtIncrease": 15,  # This changed
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }

    vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 75,  # This changed
        "activation": activation_timestamp,
        "debtRatio": 500,
        "minDebtIncrease": 15,
        "maxDebtIncrease": 15,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
    }


def test_migrateStrategy(gov, vault, strategy, rando, TestStrategy):
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})

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

    # Can't migrate back again
    with brownie.reverts():
        vault.migrateStrategy(new_strategy, strategy, {"from": gov})

    # Can't migrate an unapproved strategy
    with brownie.reverts():
        vault.migrateStrategy(new_strategy, strategy, {"from": gov})

    # Can't migrate to an already approved strategy
    approved_strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(approved_strategy, 100, 10, 20, 1000, {"from": gov})
    with brownie.reverts():
        vault.migrateStrategy(strategy, approved_strategy, {"from": gov})


def test_revokeStrategy(chain, gov, vault, strategy, rando):
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]

    # Not just anyone can revoke a strategy
    with brownie.reverts():
        vault.revokeStrategy(strategy, {"from": rando})

    vault.revokeStrategy(strategy, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 0,  # This changed
        "minDebtIncrease": 10,
        "maxDebtIncrease": 20,
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

    [vault.addStrategy(s, 100, 10, 20, 1000, {"from": gov}) for s in strategies]

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
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    strategies.append(strategy)

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # NOTE: limited to only a certain amount of strategies
    with brownie.reverts():
        vault.addStrategy(
            gov.deploy(TestStrategy, vault), 100, 10, 20, 1000, {"from": gov}
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

    # Can't add a strategy 0x0 to queue
    with brownie.reverts():
        vault.addStrategyToQueue(ZERO_ADDRESS, {"from": gov})

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

    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    vault.expectedReturn(strategy)  # Do this for coverage of `Vault._expectedReturn()`


def test_reporting_gains_without_fee(vault, token, strategy, gov, rando):
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    gain = 1000000
    token.transfer(strategy, gain, {"from": gov})
    vault.report(gain, 0, 0, {"from": strategy})


def test_withdrawalQueue(chain, gov, management, vault, strategy, other_strategy):
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    vault.addStrategy(other_strategy, 100, 10, 20, 1000, {"from": gov})

    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == other_strategy

    queue = [ZERO_ADDRESS] * 20
    queue[0] = other_strategy
    queue[1] = strategy

    vault.setWithdrawalQueue(queue, {"from": management})
    assert vault.withdrawalQueue(0) == other_strategy
    assert vault.withdrawalQueue(1) == strategy
    chain.undo()

    vault.setWithdrawalQueue(queue, {"from": gov})
    assert vault.withdrawalQueue(0) == other_strategy
    assert vault.withdrawalQueue(1) == strategy

    vault.removeStrategyFromQueue(other_strategy, {"from": management})
    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == ZERO_ADDRESS
    chain.undo()

    vault.removeStrategyFromQueue(other_strategy, {"from": gov})
    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == ZERO_ADDRESS

    vault.addStrategyToQueue(other_strategy, {"from": management})
    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == other_strategy
    chain.undo()

    vault.addStrategyToQueue(other_strategy, {"from": gov})
    assert vault.withdrawalQueue(0) == strategy
    assert vault.withdrawalQueue(1) == other_strategy


def test_update_debtRatio_to_add_second_strategy(gov, vault, strategy, other_strategy):

    vault.addStrategy(strategy, 10_000, 0, 0, 0, {"from": gov})

    # Can't add a second strategy if first one is taking 100%
    with brownie.reverts():
        vault.addStrategy(other_strategy, 5_000, 0, 0, 0, {"from": gov})

    vault.updateStrategyDebtRatio(strategy, 5_000, {"from": gov})

    # Can't add the second strategy going over 100%
    with brownie.reverts():
        vault.addStrategy(other_strategy, 5_001, 0, 0, 0, {"from": gov})

    # But 50% should work
    vault.addStrategy(other_strategy, 5_000, 0, 0, 0, {"from": gov})
