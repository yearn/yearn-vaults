def test_startup(token, gov, vault, strategy, keeper, chain):
    # Strategy has no debt or anything yet until, we call harvest
    assert token.balanceOf(strategy) == 0

    # Never reported yet
    # NOTE: done for coverage
    vault.expectedReturn(strategy) == 0

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == 0 == vault.strategies(strategy)[4]  # totalDebt

    # Take on debt
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > 0
    last_balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == vault.strategies(strategy)[4] == token.balanceOf(strategy)  # totalDebt

    # We only have 1 data point for E[R] calc, so E[R] = 0
    chain.mine(10)
    vault.expectedReturn(strategy) == 0

    # This time we've earned a return with our debt
    r = lambda: token.balanceOf(strategy) // 50
    token.transfer(strategy, r(), {"from": gov})
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > last_balance
    last_balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == vault.strategies(strategy)[4] == token.balanceOf(strategy)  # totalDebt

    # We have 2 data points for E[R] calc, so E[R] = 0
    chain.mine(10)
    vault.expectedReturn(strategy) == 0

    token.transfer(strategy, r(), {"from": gov})
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > last_balance
    last_balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == vault.strategies(strategy)[4] == token.balanceOf(strategy)  # totalDebt

    chain.mine(10)
    er = vault.expectedReturn(strategy)
    assert er > 0

    last_balance = 0
    while vault.strategies(strategy)[4] < vault.strategies(strategy)[1]:  # totalDebt  # debtLimit
        token.transfer(strategy, er, {"from": gov})
        strategy.harvest({"from": keeper})

        chain.mine(10)

        # Check balance is increasing
        assert token.balanceOf(strategy) > last_balance
        last_balance = token.balanceOf(strategy)

        # Check accounting is maintained everywhere
        assert vault.totalDebt() == vault.strategies(strategy)[4] == token.balanceOf(strategy)  # totalDebt
