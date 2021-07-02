import pytest
import brownie

DAY = 86400  # seconds


def test_emergency_shutdown(token, gov, vault, strategy, keeper, chain):
    # NOTE: totalSupply matches total investment at t = 0
    initial_investment = vault.totalSupply()
    vault.updateStrategyMaxDebtPerHarvest(
        strategy,
        (initial_investment * vault.strategies(strategy).dict()["debtRatio"] / 10_000)
        // 10,  # Run 10 times
        {"from": gov},
    )
    # Do it once to seed it with debt
    chain.sleep(1)
    strategy.harvest({"from": keeper})
    add_yield = lambda: token.transfer(
        strategy, token.balanceOf(strategy) // 50, {"from": gov}
    )

    # Just keep doing it until we're full up (should run at least once)
    debt_limit_hit = lambda: (
        vault.strategies(strategy).dict()["totalDebt"] / vault.totalAssets()
        # NOTE: Needs to hit at least 99% of the debt ratio, because 100% is unobtainable
        #       (Strategy increases it's absolute debt every harvest)
        >= 0.99 * vault.strategies(strategy).dict()["debtRatio"] / 10_000
    )
    assert not debt_limit_hit()
    while not debt_limit_hit():
        chain.sleep(DAY)
        add_yield()
        chain.sleep(1)
        strategy.harvest({"from": keeper})

    # Call for a shutdown
    vault.setEmergencyShutdown(True, {"from": gov})

    # Watch the strategy repay all its debt over time
    last_balance = token.balanceOf(strategy)
    while token.balanceOf(strategy) > 0:
        chain.sleep(DAY)
        add_yield()  # We're still vested on our positions!
        strategy.harvest({"from": keeper})

        # Make sure we are divesting
        assert token.balanceOf(strategy) <= last_balance
        last_balance = token.balanceOf(strategy)

    # All the debt is out of the system now
    assert vault.totalDebt() == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0

    # Do it once more, for good luck (and also coverage)
    token.transfer(strategy, token.balanceOf(gov), {"from": gov})
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": keeper})

    # Vault didn't lose anything during shutdown
    strategyReturn = vault.strategies(strategy).dict()["totalGain"]
    assert strategyReturn > 0
    assert token.balanceOf(vault) == initial_investment + strategyReturn


@pytest.mark.parametrize("withSurplus", [True, False])
def test_emergency_exit(token, gov, vault, strategy, keeper, chain, withSurplus):
    # NOTE: totalSupply matches total investment at t = 0
    initial_investment = vault.totalSupply()
    vault.updateStrategyMaxDebtPerHarvest(
        strategy,
        (initial_investment * vault.strategies(strategy).dict()["debtRatio"] / 10_000)
        // 10,  # Run 10 times
        {"from": gov},
    )

    # Do it once to seed it with debt
    chain.sleep(1)
    strategy.harvest({"from": keeper})
    add_yield = lambda: token.transfer(
        strategy, token.balanceOf(strategy) // 50, {"from": gov}
    )

    # Just keep doing it until we're full up (should run at least once)
    debt_limit_hit = lambda: (
        vault.strategies(strategy).dict()["totalDebt"] / vault.totalAssets()
        # NOTE: Needs to hit at least 99% of the debt ratio, because 100% is unobtainable
        #       (Strategy increases it's absolute debt every harvest)
        >= 0.99 * vault.strategies(strategy).dict()["debtRatio"] / 10_000
    )
    assert not debt_limit_hit()
    while not debt_limit_hit():
        chain.sleep(DAY)
        add_yield()
        chain.sleep(1)
        strategy.harvest({"from": keeper})

    if withSurplus:
        # Add balance to test the case in harvest() where totalAssets > debtOutstanding
        stolen_funds = 0
        added_funds = token.balanceOf(strategy) // 10
        token.transfer(strategy, added_funds, {"from": gov})
        vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    else:
        # Oh my! There was a hack!
        stolen_funds = token.balanceOf(strategy) // 10
        strategy._takeFunds(stolen_funds, {"from": gov})
        vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})

    # Call for an exit
    strategy.setEmergencyExit({"from": gov})

    # Watch the strategy repay the rest of its debt over time
    last_balance = token.balanceOf(strategy)
    while token.balanceOf(strategy) > 0:
        chain.sleep(DAY)
        strategy.harvest({"from": keeper})

        # Make sure we are divesting
        assert token.balanceOf(strategy) < last_balance
        last_balance = token.balanceOf(strategy)

    # All the debt left is out of the system now
    assert vault.totalDebt() == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
    assert vault.strategies(strategy).dict()["totalLoss"] == stolen_funds

    # Vault returned something overall though
    strategyReturn = vault.strategies(strategy).dict()["totalGain"]
    assert strategyReturn > 0
    assert token.balanceOf(vault) == initial_investment + strategyReturn - stolen_funds


def test_set_emergency_exit_authority(
    strategy, gov, strategist, keeper, rando, management, guardian
):
    # Can only setEmergencyExit as governance, strategist, vault management and guardian
    with brownie.reverts("!authorized"):
        strategy.setEmergencyExit({"from": keeper})
    with brownie.reverts("!authorized"):
        strategy.setEmergencyExit({"from": rando})
    strategy.setEmergencyExit({"from": gov})
    brownie.chain.undo()
    strategy.setEmergencyExit({"from": strategist})
    brownie.chain.undo()
    strategy.setEmergencyExit({"from": management})
    brownie.chain.undo()
    strategy.setEmergencyExit({"from": guardian})
