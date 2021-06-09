import brownie

from brownie import ZERO_ADDRESS


def test_good_migration(
    token, strategy, vault, gov, strategist, guardian, TestStrategy, rando, chain
):
    # Call this once to seed the strategy with debt
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    strategy_debt = vault.strategies(strategy).dict()["totalDebt"]
    assert strategy_debt == token.balanceOf(strategy)

    new_strategy = strategist.deploy(TestStrategy, vault)
    assert vault.strategies(new_strategy).dict()["totalDebt"] == 0
    assert token.balanceOf(new_strategy) == 0

    # Only Governance can migrate
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": rando})
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": strategist})
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": guardian})

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert (
        vault.strategies(strategy).dict()["totalDebt"] == token.balanceOf(strategy) == 0
    )
    assert (
        vault.strategies(new_strategy).dict()["totalDebt"]
        == token.balanceOf(new_strategy)
        == strategy_debt
    )

    with brownie.reverts():
        new_strategy.migrate(strategy, {"from": gov})


def test_bad_migration(
    token, vault, strategy, gov, strategist, TestStrategy, Vault, rando
):
    different_vault = gov.deploy(Vault)
    different_vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    different_vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    new_strategy = strategist.deploy(TestStrategy, different_vault)

    # Can't migrate to a strategy with a different vault
    with brownie.reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    new_strategy = strategist.deploy(TestStrategy, vault)

    # Can't migrate if you're not the Vault  or governance
    with brownie.reverts():
        strategy.migrate(new_strategy, {"from": rando})

    # Can't migrate if new strategy is 0x0
    with brownie.reverts():
        vault.migrateStrategy(strategy, ZERO_ADDRESS, {"from": gov})


def test_migrated_strategy_can_call_harvest(
    token, strategy, vault, gov, TestStrategy, chain
):

    new_strategy = gov.deploy(TestStrategy, vault)
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # send profit to the old strategy
    token.transfer(strategy, 10 ** token.decimals(), {"from": gov})

    assert vault.strategies(strategy).dict()["totalGain"] == 0
    chain.sleep(1)
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["totalGain"] == 10 ** token.decimals()

    # But after migrated it cannot be added back
    vault.updateStrategyDebtRatio(new_strategy, 5_000, {"from": gov})
    with brownie.reverts():
        vault.addStrategy(strategy, 5_000, 0, 1000, 0, {"from": gov})
