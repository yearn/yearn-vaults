DAY = 86400  # seconds


def test_startup(token, gov, vault, strategy, keeper, chain):
    debt_per_harvest = (
        (vault.totalAssets() - vault.totalDebt()) * (vault.debtRatio() / 10_000)
    ) // 10  # 10 harvests, or about 8 loop iterations
    vault.updateStrategyMaxDebtPerHarvest(strategy, debt_per_harvest, {"from": gov})
    expectedReturn = lambda: vault.expectedReturn(strategy)

    # Never reported yet (no data points)
    # NOTE: done for coverage
    assert expectedReturn() == 0

    # Check accounting is maintained everywhere
    assert token.balanceOf(vault) > 0
    assert vault.totalAssets() == token.balanceOf(vault)
    assert (
        vault.totalDebt()
        == vault.strategies(strategy).dict()["totalDebt"]
        == strategy.estimatedTotalAssets()
        == token.balanceOf(strategy)
        == 0
    )

    # Take on debt
    chain.mine(timestamp=chain.time() + DAY)
    assert vault.expectedReturn(strategy) == 0
    chain.sleep(1)
    strategy.harvest({"from": keeper})

    # Check balance is increasing
    assert token.balanceOf(strategy) > 0
    balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalAssets() == token.balanceOf(vault) + balance
    assert (
        vault.totalDebt()
        == vault.strategies(strategy).dict()["totalDebt"]
        == strategy.estimatedTotalAssets()
        == balance
    )

    # We have 1 data point for E[R] calc w/ no profits, so E[R] = 0
    chain.mine(timestamp=chain.time() + DAY)
    assert expectedReturn() == 0

    profit = token.balanceOf(strategy) // 50
    assert profit > 0
    token.transfer(strategy, profit, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": keeper})
    assert vault.strategies(strategy).dict()["totalGain"] == profit

    # Check balance is increasing
    assert token.balanceOf(strategy) > balance
    balance = token.balanceOf(strategy)

    # Check accounting is maintained everywhere
    assert vault.totalAssets() == token.balanceOf(vault) + balance
    assert (
        vault.totalDebt()
        == vault.strategies(strategy).dict()["totalDebt"]
        == strategy.estimatedTotalAssets()
        == balance
    )

    # Ramp up debt (Should execute at least once)
    debt_limit_hit = lambda: (
        vault.strategies(strategy).dict()["totalDebt"] / vault.totalAssets()
        # NOTE: Needs to hit at least 99% of the debt ratio, because 100% is unobtainable
        #       (Strategy increases it's absolute debt every harvest)
        >= 0.99 * vault.strategies(strategy).dict()["debtRatio"] / 10_000
    )
    assert not debt_limit_hit()
    while not debt_limit_hit():

        chain.mine(timestamp=chain.time() + DAY)
        assert expectedReturn() > 0
        token.transfer(strategy, expectedReturn(), {"from": gov})
        chain.sleep(1)
        strategy.harvest({"from": keeper})

        # Check balance is increasing
        assert token.balanceOf(strategy) > balance
        balance = token.balanceOf(strategy)

        # Check accounting is maintained everywhere
        assert vault.totalAssets() == token.balanceOf(vault) + balance
        assert (
            vault.totalDebt()
            == vault.strategies(strategy).dict()["totalDebt"]
            == strategy.estimatedTotalAssets()
            == balance
        )
