DAY = 86400  # seconds


def test_emergency_shutdown(token, gov, vault, strategy, keeper, chain):
    # NOTE: totalSupply matches total investment at t = 0
    initial_investment = vault.totalSupply()
    # Do it once to seed it with debt
    strategy.harvest({"from": keeper})
    add_yield = lambda: token.transfer(
        strategy, token.balanceOf(strategy) // 50, {"from": gov}
    )

    # Just keep doing it until we're full up
    while (
        vault.strategies(strategy).dict()["totalDebt"]
        < vault.strategies(strategy).dict()["debtLimit"]
    ):
        chain.sleep(DAY)
        add_yield()
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
    strategy.harvest({"from": keeper})

    # Vault didn't lose anything during shutdown
    strategyReturn = vault.strategies(strategy).dict()["totalGain"]
    assert strategyReturn > 0
    assert token.balanceOf(vault) == initial_investment + strategyReturn


def test_emergency_exit(token, gov, vault, strategy, keeper, chain):
    # NOTE: totalSupply matches total investment at t = 0
    initial_investment = vault.totalSupply()
    # Do it once to seed it with debt
    strategy.harvest({"from": keeper})
    add_yield = lambda: token.transfer(
        strategy, token.balanceOf(strategy) // 50, {"from": gov}
    )

    # Just keep doing it until we're full up
    while (
        vault.strategies(strategy).dict()["totalDebt"]
        < vault.strategies(strategy).dict()["debtLimit"]
    ):
        chain.sleep(DAY)
        add_yield()
        strategy.harvest({"from": keeper})

    # Oh my! There was a hack!
    stolen_funds = token.balanceOf(strategy) // 10
    strategy._takeFunds(stolen_funds, {"from": gov})

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
    assert vault.totalDebt() == stolen_funds
    assert vault.strategies(strategy).dict()["totalDebt"] == stolen_funds

    # Vault returned something overall though
    strategyReturn = vault.strategies(strategy).dict()["totalGain"]
    assert strategyReturn > 0
    assert token.balanceOf(vault) == initial_investment + strategyReturn - stolen_funds
