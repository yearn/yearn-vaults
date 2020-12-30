import brownie


def test_multiple_withdrawals(chain, token, gov, Vault, TestStrategy):
    # Need a fresh vault to do this math right
    vault = Vault.deploy({"from": gov})
    vault.initialize(
        token,
        gov,
        gov,
        token.symbol() + " yVault",
        "yv" + token.symbol(),
        gov,
        {"from": gov},
    )
    starting_balance = token.balanceOf(gov)
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(5)]
    [
        vault.addStrategy(
            s,
            token.balanceOf(gov) // 10,  # 10% of all tokens
            2 ** 256 - 1,  # No rate limit
            0,  # No fee
            {"from": gov},
        )
        for s in strategies
    ]

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit({"from": gov})

    assert token.balanceOf(gov) == 0
    assert token.balanceOf(vault) == starting_balance

    chain.sleep(8640)
    [s.harvest({"from": gov}) for s in strategies]  # Seed all the strategies with debt

    assert token.balanceOf(vault) == starting_balance // 2
    for s in strategies:  # All of them have debt
        assert (
            vault.balanceSheetOfStrategy(s)
            == token.balanceOf(s)
            == starting_balance // 10
        )

    # Withdraw only from Vault
    before = token.balanceOf(vault)
    vault.withdraw(vault.balanceOf(gov) // 2 + 1, {"from": gov})
    assert token.balanceOf(vault) == 0
    assert token.balanceOf(gov) == before
    for s in strategies:
        assert (
            vault.balanceSheetOfStrategy(s)
            == token.balanceOf(s)
            == starting_balance // 10
        )

    # We've drained all the debt
    vault.withdraw(vault.balanceOf(gov), {"from": gov})
    for s in strategies:
        assert vault.balanceSheetOfStrategy(s) == 0
        assert token.balanceOf(s) == 0

    assert vault.totalDebt() == 0
    for s in strategies:
        assert vault.balanceSheetOfStrategy(s) == token.balanceOf(s) == 0


def test_forced_withdrawal(token, gov, vault, TestStrategy, rando, chain):
    # Add strategies
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(5)]
    [vault.addStrategy(s, 1000, 10, 1000, {"from": gov}) for s in strategies]

    # Send tokens to random user
    token.approve(gov, 2 ** 256 - 1, {"from": gov})
    token.transferFrom(gov, rando, 1000, {"from": gov})
    assert token.balanceOf(rando) == 1000

    # rando and gov deposits tokens to the vault
    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    token.approve(vault, 2 ** 256 - 1, {"from": rando})
    vault.deposit(1000, {"from": rando})
    vault.deposit(4000, {"from": gov})

    assert token.balanceOf(rando) == 0
    assert vault.balanceOf(rando) > 0
    assert vault.balanceOf(gov) > 0

    # Withdrawal should fail, no matter the distribution of tokens between
    # the vault and the strategies
    while vault.totalDebt() < vault.debtLimit():
        chain.sleep(86400)  # wait a day
        [s.harvest({"from": gov}) for s in strategies]
        with brownie.reverts():
            vault.withdraw(5000, {"from": rando})


def test_progressive_withdrawal(
    chain, token, gov, Vault, guardian, rewards, TestStrategy
):
    vault = guardian.deploy(Vault)
    vault.initialize(
        token, gov, rewards, token.symbol() + " yVault", "yv" + token.symbol(), guardian
    )

    strategies = [gov.deploy(TestStrategy, vault) for _ in range(2)]
    [vault.addStrategy(s, 1000, 10, 1000, {"from": gov}) for s in strategies]

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit(1000, {"from": gov})
    token.approve(gov, 2 ** 256 - 1, {"from": gov})
    token.transferFrom(
        gov, guardian, token.balanceOf(gov), {"from": gov}
    )  # Remove all tokens from gov
    assert vault.balanceOf(gov) > 0
    assert token.balanceOf(gov) == 0

    # Deposit something in strategies
    chain.sleep(1)  # Needs to be a second ahead, at least
    [s.harvest({"from": gov}) for s in strategies]
    assert token.balanceOf(vault) < vault.totalAssets()  # Some debt is in strategies

    # First withdraw everything possible without fees
    free_balance = token.balanceOf(vault)
    vault.withdraw(
        free_balance * vault.pricePerShare() // 10 ** vault.decimals(), {"from": gov}
    )
    assert token.balanceOf(gov) == free_balance
    assert vault.balanceOf(gov) > 0

    # Then withdraw everything from the first strategy
    balance_strat1 = token.balanceOf(strategies[0])
    assert balance_strat1 > 0
    vault.withdraw(
        balance_strat1 * vault.pricePerShare() // 10 ** vault.decimals(), {"from": gov}
    )
    assert token.balanceOf(gov) == free_balance + balance_strat1
    assert vault.balanceOf(gov) > 0
    assert vault.maxAvailableShares() == token.balanceOf(strategies[1])

    # Withdraw the final part
    balance_strat2 = token.balanceOf(strategies[1])
    assert balance_strat2 > 0
    vault.withdraw(
        balance_strat2 * vault.pricePerShare() // 10 ** vault.decimals(), {"from": gov}
    )
    assert token.balanceOf(gov) == free_balance + balance_strat1 + balance_strat2
    assert vault.balanceOf(gov) == 0
    assert token.balanceOf(vault) == 0


def test_withdrawal_with_empty_queue(
    chain, token, gov, Vault, guardian, rewards, TestStrategy
):
    vault = guardian.deploy(Vault)
    vault.initialize(
        token, gov, rewards, token.symbol() + " yVault", "yv" + token.symbol(), guardian
    )

    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 1000, 10, 1000, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit(1000, {"from": gov})

    # Remove all tokens from gov to make asserts easier
    token.approve(gov, 2 ** 256 - 1, {"from": gov})
    token.transferFrom(gov, guardian, token.balanceOf(gov), {"from": gov})

    chain.sleep(8640)
    strategy.harvest({"from": gov})
    assert token.balanceOf(vault) < vault.totalAssets()

    vault.removeStrategyFromQueue(strategy, {"from": gov})

    free_balance = token.balanceOf(vault)
    strategy_balance = token.balanceOf(strategy)
    assert (
        vault.balanceOf(gov) == 1000 * vault.pricePerShare() // 10 ** vault.decimals()
    )
    vault.withdraw(
        1000 * vault.pricePerShare() // 10 ** vault.decimals(), {"from": gov}
    )

    # This means withdrawal will not revert even when we didn't get the total amount back
    assert vault.balanceOf(gov) == strategy_balance
    assert token.balanceOf(gov) == free_balance

    # Calling it a second time with strategy_balance should be a no-op
    vault.withdraw(
        strategy_balance * vault.pricePerShare() // 10 ** vault.decimals(),
        {"from": gov},
    )
    assert token.balanceOf(gov) == free_balance

    # Re-establish the withdrawal queue
    vault.addStrategyToQueue(strategy, {"from": gov})

    vault.withdraw(
        strategy_balance * vault.pricePerShare() // 10 ** vault.decimals(),
        {"from": gov},
    )
    assert token.balanceOf(gov) == free_balance + strategy_balance
