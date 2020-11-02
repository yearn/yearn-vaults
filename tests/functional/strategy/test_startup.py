def test_startup(token, gov, vault, strategy, keeper, chain):
    # Strategy has no debt or anything yet until, we call harvest
    assert token.balanceOf(strategy) == 0

    # Never reported yet
    # NOTE: done for coverage
    vault.expectedReturn(strategy) == 0
    assert vault.balanceSheetOfStrategy(strategy) == 0
    assert not strategy.harvestTrigger(0)
    chain.mine(50)
    assert strategy.harvestTrigger(0)

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == 0 == vault.strategies(strategy)[5]  # totalDebt
    withdrawal_queue = [strategy] + ["0x0000000000000000000000000000000000000000"] * 39
    assert vault.totalBalanceSheet(withdrawal_queue) == token.balanceOf(vault)

    # Take on debt
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > 0
    last_balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == vault.strategies(strategy)[5]  # totalDebt
    assert vault.balanceSheetOfStrategy(strategy) == vault.totalDebt()
    assert (
        vault.totalBalanceSheet(withdrawal_queue)
        == token.balanceOf(vault) + vault.totalDebt()
    )

    # We have 1 data point for E[R] calc, so E[R] = 0
    chain.mine(10)
    assert vault.expectedReturn(strategy) == 0

    r = lambda: token.balanceOf(strategy) // 50
    token.transfer(strategy, r(), {"from": gov})
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > last_balance
    last_balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalDebt() == vault.strategies(strategy)[5]  # totalDebt
    assert vault.balanceSheetOfStrategy(strategy) == vault.totalDebt()
    assert (
        vault.totalBalanceSheet(withdrawal_queue)
        == token.balanceOf(vault) + vault.totalDebt()
    )

    # We have 2 data points now, so E[R] > 0
    chain.mine(10)
    er = vault.expectedReturn(strategy)
    assert er > 0

    last_balance = 0
    while (
        vault.strategies(strategy)[5] < vault.strategies(strategy)[2]
    ):  # totalDebt  # debtLimit
        token.transfer(strategy, er, {"from": gov})
        strategy.harvest({"from": keeper})

        chain.mine(10)

        # Check balance is increasing
        assert token.balanceOf(strategy) > last_balance
        last_balance = token.balanceOf(strategy)

        # Check accounting is maintained everywhere
        assert vault.totalDebt() == vault.strategies(strategy)[5]  # totalDebt
        assert vault.balanceSheetOfStrategy(strategy) == vault.totalDebt()
        assert (
            vault.totalBalanceSheet(withdrawal_queue)
            == token.balanceOf(vault) + vault.totalDebt()
        )
