import brownie


def test_reduce_debt_ratio(token, strategy, vault, gov, TestStrategy, chain):

    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["totalDebt"] > 0
    old_debt_ratio = vault.strategies(strategy).dict()["debtRatio"]
    vault.updateStrategyDebtRatio(strategy, old_debt_ratio // 2, {"from": gov})

    assert vault.debtOutstanding(strategy) > 0
