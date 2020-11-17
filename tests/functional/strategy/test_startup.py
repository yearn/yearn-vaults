DAY = 86400  # seconds


def test_startup(token, gov, vault, strategy, keeper, chain):
    all_strategies = [strategy] + ["0x0000000000000000000000000000000000000000"] * 39
    expectedReturn = lambda: vault.expectedReturn(strategy)

    # Never reported yet (no data points)
    # NOTE: done for coverage
    assert expectedReturn() == 0

    # Check accounting is maintained everywhere
    assert token.balanceOf(vault) > 0
    assert (
        vault.totalAssets()
        == vault.totalBalanceSheet(all_strategies)
        == token.balanceOf(vault)
    )
    assert (
        vault.totalDebt()
        == vault.strategies(strategy).dict()["totalDebt"]
        == vault.balanceSheetOfStrategy(strategy)
        == token.balanceOf(strategy)
        == 0
    )

    # Take on debt
    chain.mine(timestamp=chain.time() + DAY)
    assert vault.expectedReturn(strategy) == 0
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > 0
    balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert (
        vault.totalAssets()
        == vault.totalBalanceSheet(all_strategies)
        == token.balanceOf(vault) + balance
    )
    assert (
        vault.totalDebt()
        == vault.strategies(strategy).dict()["totalDebt"]
        == vault.balanceSheetOfStrategy(strategy)
        == balance
    )

    # We have 1 data point for E[R] calc w/ no profits, so E[R] = 0
    chain.mine(timestamp=chain.time() + DAY)
    assert expectedReturn() == 0

    profit = token.balanceOf(strategy) // 50
    assert profit > 0
    token.transfer(strategy, profit, {"from": gov})
    strategy.harvest({"from": keeper})
    assert vault.strategies(strategy).dict()["totalGain"] == profit

    # Check balance is increasing
    assert token.balanceOf(strategy) > balance
    balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert (
        vault.totalAssets()
        == vault.totalBalanceSheet(all_strategies)
        == token.balanceOf(vault) + balance
    )
    assert (
        vault.totalDebt()
        == vault.strategies(strategy).dict()["totalDebt"]
        == vault.balanceSheetOfStrategy(strategy)
        == balance
    )

    # Ramp up debt (Should execute at least once)
    debt_limit_hit = lambda: (
        vault.strategies(strategy).dict()["totalDebt"]
        == vault.strategies(strategy).dict()["debtLimit"]
    )
    assert not debt_limit_hit()
    while not debt_limit_hit():

        chain.mine(timestamp=chain.time() + DAY)
        assert expectedReturn() > 0
        token.transfer(strategy, expectedReturn(), {"from": gov})
        strategy.harvest({"from": keeper})

        # Check balance is increasing
        assert token.balanceOf(strategy) > balance
        balance = token.balanceOf(strategy)

        # Check accounting is maintained everywhere
        assert (
            vault.totalAssets()
            == vault.totalBalanceSheet(all_strategies)
            == token.balanceOf(vault) + balance
        )
        assert (
            vault.totalDebt()
            == vault.strategies(strategy).dict()["totalDebt"]
            == vault.balanceSheetOfStrategy(strategy)
            == balance
        )
