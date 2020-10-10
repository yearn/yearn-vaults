def test_emergency_shutdown(token, gov, vault, strategy, keeper, chain):
    # NOTE: totalSupply matches total investment at t = 0
    initial_investment = vault.totalSupply()
    # Do it once to seed it with debt
    strategy.harvest({"from": keeper})
    add_yield = lambda: token.transfer(
        strategy, token.balanceOf(strategy) // 50, {"from": gov}
    )

    # Just keep doing it until we're full up
    while vault.strategies(strategy)[5] < vault.strategies(strategy)[2]:
        chain.mine(10)
        add_yield()
        strategy.harvest({"from": keeper})

    # Call for a shutdown
    vault.setEmergencyShutdown(True, {"from": gov})

    # Watch the strategy repay all its debt over time
    last_balance = token.balanceOf(strategy)
    while token.balanceOf(strategy) > 0:
        chain.mine(10)
        add_yield()  # We're still vested on our positions!
        strategy.harvest({"from": keeper})

        # Make sure we are divesting
        assert token.balanceOf(strategy) <= last_balance
        last_balance = token.balanceOf(strategy)

    # All the debt is out of the system now
    assert vault.totalDebt() == 0
    assert vault.strategies(strategy)[5] == 0
    assert strategy.outstanding() == 0

    # Do it once more, for good luck (and also coverage)
    token.transfer(strategy, token.balanceOf(gov), {"from": gov})
    strategy.harvest({"from": keeper})

    # Vault didn't lose anything during shutdown
    strategyReturn = vault.strategies(strategy)[6]
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
    while vault.strategies(strategy)[5] < vault.strategies(strategy)[2]:
        chain.mine(10)
        add_yield()
        strategy.harvest({"from": keeper})

    # Call for an exit
    strategy.setEmergencyExit({"from": gov})

    # Watch the strategy repay all its debt over time
    last_balance = token.balanceOf(strategy)
    while token.balanceOf(strategy) > 0:
        chain.mine(10)
        strategy.harvest({"from": keeper})

        # Make sure we are divesting
        assert token.balanceOf(strategy) < last_balance
        last_balance = token.balanceOf(strategy)

    # All the debt is out of the system now
    assert vault.totalDebt() == 0
    assert vault.strategies(strategy)[5] == 0
    assert strategy.outstanding() == 0

    # Vault didn't lose anything during shutdown
    strategyReturn = vault.strategies(strategy)[6]
    assert strategyReturn > 0
    assert token.balanceOf(vault) == initial_investment + strategyReturn
