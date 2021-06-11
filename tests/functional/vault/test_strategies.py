import pytest
import brownie
from brownie import ZERO_ADDRESS

MAX_UINT256 = 2 ** 256 - 1


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
def other_token(gov, Token):
    yield gov.deploy(Token, 18)


def test_liquidation_after_hack(chain, gov, vault, token, TestStrategy):
    # Deposit into vault
    token.approve(vault, MAX_UINT256, {"from": gov})
    vault.deposit(1000, {"from": gov})

    # Deploy strategy and seed it with debt
    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 2_000, 0, 10 ** 21, 1000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    # The strategy suffers a loss
    stolenFunds = token.balanceOf(strategy) // 2
    strategy._takeFunds(stolenFunds, {"from": gov})
    strategyTotalAssetsAfterHack = token.balanceOf(strategy)

    # Make sure strategy debt exceeds strategy assets
    totalDebt = vault.strategies(strategy).dict()["totalDebt"]
    totalAssets = token.balanceOf(strategy)
    assert totalDebt > totalAssets

    # Make sure the withdrawal results in liquidation
    amountToWithdraw = 100  # amountNeeded in BaseStrategy
    assert amountToWithdraw <= strategyTotalAssetsAfterHack
    loss = totalDebt - totalAssets
    assert loss <= amountToWithdraw

    # Liquidate strategy
    strategy.withdraw(amountToWithdraw, {"from": vault})


@pytest.fixture
def strategy_with_wrong_vault(gov, token, vault, Vault, TestStrategy):
    otherVault = gov.deploy(Vault)
    otherVault.initialize(
        token,
        gov,
        gov,
        token.symbol() + " yVault",
        "yv" + token.symbol(),
        gov,
    )
    assert otherVault.token() == token
    assert otherVault != vault
    otherVault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    yield gov.deploy(TestStrategy, otherVault)


@pytest.fixture
def strategy_with_wrong_want_token(gov, vault, other_token, Token, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    assert strategy.want() == vault.token()
    assert strategy.vault() == vault
    strategy._setWant(other_token)
    assert strategy.want() == other_token
    yield strategy


def test_addStrategy(
    chain,
    gov,
    vault,
    strategy,
    other_strategy,
    strategy_with_wrong_want_token,
    strategy_with_wrong_vault,
    rando,
):

    # Only governance can add a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": rando})

    # Can't add a strategy during emergency shutdown
    vault.setEmergencyShutdown(True, {"from": gov})
    with brownie.reverts():
        vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    chain.undo()
    chain.undo()

    assert vault.strategies(strategy).dict() == {
        "performanceFee": 0,
        "activation": 0,
        "debtRatio": 0,
        "minDebtPerHarvest": 0,
        "maxDebtPerHarvest": 0,
        "lastReport": 0,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "enforceChangeLimit": False,
        "lossLimitRatio": 0,
        "profitLimitRatio": 0,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }

    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 100,
        "minDebtPerHarvest": 10,
        "maxDebtPerHarvest": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "enforceChangeLimit": True,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }
    assert vault.withdrawalQueue(0) == strategy

    # Can't add a strategy twice
    with brownie.reverts():
        vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})

    # Can't add zero address as a strategy
    with brownie.reverts():
        vault.addStrategy(ZERO_ADDRESS, 100, 10, 20, 1000, {"from": gov})

    # Can't add a strategy with incorrect vault
    with brownie.reverts():
        vault.addStrategy(strategy_with_wrong_vault, 100, 10, 20, 1000, {"from": gov})

    # Can't add a strategy with incorrect want token
    with brownie.reverts():
        vault.addStrategy(
            strategy_with_wrong_want_token, 100, 10, 20, 1000, {"from": gov}
        )

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
        vault.updateStrategyMinDebtPerHarvest(strategy, 15, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyMaxDebtPerHarvest(strategy, 15, {"from": gov})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})

    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    activation_timestamp = chain[-1]["timestamp"]

    # Not just anyone can update a strategy
    with brownie.reverts():
        vault.updateStrategyDebtRatio(strategy, 500, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyMinDebtPerHarvest(strategy, 15, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyMaxDebtPerHarvest(strategy, 15, {"from": rando})
    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy, 75, {"from": rando})

    vault.updateStrategyDebtRatio(strategy, 500, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "activation": activation_timestamp,
        "debtRatio": 500,  # This changed
        "performanceFee": 1000,
        "minDebtPerHarvest": 10,
        "maxDebtPerHarvest": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "enforceChangeLimit": True,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }

    vault.updateStrategyMinDebtPerHarvest(strategy, 15, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 500,
        "minDebtPerHarvest": 15,  # This changed
        "maxDebtPerHarvest": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "enforceChangeLimit": True,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }

    vault.updateStrategyMaxDebtPerHarvest(strategy, 15, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "activation": activation_timestamp,
        "debtRatio": 500,
        "minDebtPerHarvest": 15,
        "maxDebtPerHarvest": 15,  # This changed
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "enforceChangeLimit": True,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }

    vault.updateStrategyPerformanceFee(strategy, 75, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "performanceFee": 75,  # This changed
        "activation": activation_timestamp,
        "debtRatio": 500,
        "minDebtPerHarvest": 15,
        "maxDebtPerHarvest": 15,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "enforceChangeLimit": True,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }


def test_migrateStrategy(gov, vault, strategy, other_strategy, rando, TestStrategy):
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})

    # Not just anyone can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, rando, {"from": rando})

    # Can't migrate to itself
    with brownie.reverts():
        vault.migrateStrategy(strategy, strategy, {"from": gov})

    # Can't migrate from an unactivated strategy
    with brownie.reverts():
        vault.migrateStrategy(other_strategy, strategy, {"from": gov})

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
    # do not revoke twice
    with brownie.reverts():
        vault.revokeStrategy(strategy, {"from": gov})
    # do not revoke non-existing strategy
    with brownie.reverts():
        vault.revokeStrategy(ZERO_ADDRESS, {"from": gov})

    assert vault.strategies(strategy).dict() == {
        "performanceFee": 1000,
        "enforceChangeLimit": True,
        "activation": activation_timestamp,
        "debtRatio": 0,  # This changed
        "minDebtPerHarvest": 10,
        "maxDebtPerHarvest": 20,
        "lastReport": activation_timestamp,
        "totalGain": 0,
        "totalLoss": 0,
        "totalDebt": 0,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "customCheck": "0x0000000000000000000000000000000000000000",
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
            strategies + [ZERO_ADDRESS] * (20 - len(strategies)),
            {"from": gov},
        )

    for s in strategies:
        vault.addStrategy(s, 100, 10, 20, 1000, {"from": gov})

    for idx, strategy in enumerate(strategies):
        assert vault.withdrawalQueue(idx) == strategy

    # Show that strategies can be reordered
    strategies = list(reversed(strategies))
    # NOTE: Not just anyone can do this
    with brownie.reverts():
        vault.setWithdrawalQueue(
            strategies + [ZERO_ADDRESS] * (20 - len(strategies)),
            {"from": rando},
        )
    vault.setWithdrawalQueue(
        strategies + [ZERO_ADDRESS] * (20 - len(strategies)),
        {"from": gov},
    )

    other_strat = gov.deploy(TestStrategy, vault)

    # Do not add a strategy
    with brownie.reverts():
        vault.setWithdrawalQueue(
            strategies + [other_strat] * (20 - len(strategies)),
            {"from": gov},
        )

    # Do not remove strategies
    with brownie.reverts():
        vault.setWithdrawalQueue(
            strategies[0:-2] + [ZERO_ADDRESS] * (20 - len(strategies[0:-2])),
            {"from": gov},
        )

    # Do not add new strategies
    other_strategy_list = strategies.copy()
    other_strategy_list[0] = other_strat
    with brownie.reverts():
        vault.setWithdrawalQueue(
            other_strategy_list + [ZERO_ADDRESS] * (20 - len(other_strategy_list)),
            {"from": gov},
        )

    # can't use the same strategy twice
    with brownie.reverts():
        vault.setWithdrawalQueue(
            [strategies[0], strategies[0]] + [ZERO_ADDRESS] * 18,
            {"from": rando},
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


def test_addStategyToQueue(
    gov, management, vault, TestStrategy, strategy, other_strategy, rando
):
    # Can't add an unactivated strategy to queue
    with brownie.reverts():
        vault.addStrategyToQueue(strategy, {"from": gov})

    # Initialize strategies (keep other_strategy in queue to test the queue)
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    vault.removeStrategyFromQueue(strategy, {"from": gov})
    vault.addStrategy(other_strategy, 100, 10, 20, 1000, {"from": gov})

    # Not just anyone can add a strategy to the queue
    with brownie.reverts():
        vault.addStrategyToQueue(strategy, {"from": rando})

    # Governance can add a strategy to the queue
    vault.addStrategyToQueue(strategy, {"from": gov})
    vault.removeStrategyFromQueue(strategy, {"from": gov})

    # Management can add a strategy to the queue
    vault.addStrategyToQueue(strategy, {"from": management})
    vault.removeStrategyFromQueue(strategy, {"from": management})

    # Can't add an existing strategy to the queue
    vault.addStrategyToQueue(strategy, {"from": gov})
    with brownie.reverts():
        vault.addStrategyToQueue(strategy, {"from": gov})
    vault.removeStrategyFromQueue(strategy, {"from": gov})
    vault.removeStrategyFromQueue(other_strategy, {"from": gov})

    # Can't add a strategy to an already full queue
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(20)]
    for s in strategies:
        vault.addStrategy(s, 100, 10, 20, 1000, {"from": gov})
    with brownie.reverts():
        vault.addStrategyToQueue(strategy, {"from": gov})


def test_reporting(vault, token, strategy, gov, rando):
    # Not just anyone can call `Vault.report()`
    with brownie.reverts():
        vault.report(0, 0, 0, {"from": rando})

    strategy.tend({"from": gov})  # Do this for converage of `Strategy.tend()`

    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    vault.expectedReturn(strategy)  # Do this for coverage of `Vault._expectedReturn()`

    # Can't have more loss than strategy debt
    strategyTokenBalance = token.balanceOf(strategy)
    assert strategyTokenBalance == 0
    debt = vault.totalDebt()
    loss = 1000
    assert debt == 0
    assert loss >= debt
    with brownie.reverts():
        vault.report(0, loss, 0, {"from": strategy})


def test_reporting_gains_without_fee(chain, vault, token, strategy, gov, rando):
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.addStrategy(strategy, 100, 10, 20, 1000, {"from": gov})
    gain = 1000000
    assert token.balanceOf(strategy) == 0
    chain.sleep(1)

    # Can't lie about total available to withdraw
    with brownie.reverts():
        vault.report(gain, 0, 0, {"from": strategy})

    token.transfer(strategy, gain, {"from": gov})
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})

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


def test_health_report_check(gov, token, vault, strategy, chain):
    token.approve(vault, MAX_UINT256, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 1000, 0, {"from": gov})
    vault.deposit(1000, {"from": gov})
    chain.sleep(1)
    strategy.harvest()

    # Small price change won't trigger the emergency
    price = vault.pricePerShare()
    strategy._takeFunds(30, {"from": gov})
    chain.sleep(1)
    strategy.harvest()
    assert vault.pricePerShare() == 0.97 * 10 ** vault.decimals()

    # Big price change isn't allowed
    strategy._takeFunds(100, {"from": gov})
    chain.sleep(1)
    with brownie.reverts():
        strategy.harvest()
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    strategy.harvest()
    assert vault.pricePerShare() == 0.87 * 10 ** vault.decimals()

    strategy._takeFunds(token.balanceOf(strategy) / 10, {"from": gov})
    chain.sleep(1)
    with brownie.reverts():
        strategy.harvest()
    vault.setStrategySetLimitRatio(strategy, 1000, 1000)  # 10%
    strategy.harvest()
    assert vault.pricePerShare() == 0.786 * 10 ** vault.decimals()


def test_custom_health_check(gov, token, vault, strategy, chain, TestHealthCheck):
    token.approve(vault, MAX_UINT256, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 1000, 0, {"from": gov})
    vault.deposit(1000, {"from": gov})
    chain.sleep(1)
    strategy.harvest()
    check = TestHealthCheck.deploy({"from": gov})
    vault.setStrategyCustomCheck(strategy, check, {"from": gov})
    strategy._takeFunds(100, {"from": gov})
    chain.sleep(1)
    strategy.harvest()
    check.togglePass()
    chain.sleep(1)
    with brownie.reverts():
        strategy.harvest()


def test_update_healt_check_report(gov, rando, vault, strategy, chain):
    vault.addStrategy(strategy, 10_000, 0, 1000, 0, {"from": gov})

    activation_timestamp = chain[-1]["timestamp"]
    # Not just anyone can update heath check report
    with brownie.reverts():
        vault.setStrategyEnforceChangeLimit(strategy, False, {"from": rando})
    with brownie.reverts():
        vault.setStrategySetLimitRatio(strategy, 50, 50, {"from": rando})

    vault.setStrategyEnforceChangeLimit(strategy, True, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "activation": activation_timestamp,
        "debtRatio": 10000,
        "enforceChangeLimit": True,
        "lossLimitRatio": 300,
        "profitLimitRatio": 300,
        "lastReport": activation_timestamp,
        "maxDebtPerHarvest": 1000,
        "minDebtPerHarvest": 0,
        "performanceFee": 0,
        "totalDebt": 0,
        "totalGain": 0,
        "totalLoss": 0,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }

    vault.setStrategySetLimitRatio(strategy, 50, 50, {"from": gov})
    assert vault.strategies(strategy).dict() == {
        "activation": activation_timestamp,
        "debtRatio": 10000,
        "enforceChangeLimit": True,
        "lossLimitRatio": 50,
        "profitLimitRatio": 50,
        "lastReport": activation_timestamp,
        "maxDebtPerHarvest": 1000,
        "minDebtPerHarvest": 0,
        "performanceFee": 0,
        "totalDebt": 0,
        "totalGain": 0,
        "totalLoss": 0,
        "customCheck": "0x0000000000000000000000000000000000000000",
    }
