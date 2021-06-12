import brownie


def test_multiple_withdrawals(token, gov, Vault, TestStrategy, chain):
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
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit(1_000_000, {"from": gov})

    starting_balance = token.balanceOf(vault)
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(5)]
    for s in strategies:
        vault.addStrategy(
            s,
            1_000,  # 10% of all tokens in Vault
            0,
            2 ** 256 - 1,  # No harvest limit
            0,  # No fee
            {"from": gov},
        )
    chain.sleep(1)

    for s in strategies:  # Seed all the strategies with debt
        s.harvest({"from": gov})

    assert token.balanceOf(vault) == starting_balance // 2  # 50% in strategies
    for s in strategies:  # All of them have debt (10% each)
        assert s.estimatedTotalAssets() == token.balanceOf(s) == starting_balance // 10

    # Withdraw only from Vault
    vault.withdraw(vault.balanceOf(gov) // 2, {"from": gov})
    assert token.balanceOf(vault) == 0
    for s in strategies:  # No change
        assert s.estimatedTotalAssets() == token.balanceOf(s) == starting_balance // 10

    # We've drained all the debt
    vault.withdraw(vault.balanceOf(gov), {"from": gov})
    assert vault.totalDebt() == 0
    for s in strategies:
        assert s.estimatedTotalAssets() == 0
        assert token.balanceOf(s) == 0


def test_forced_withdrawal(token, gov, vault, TestStrategy, rando, chain):
    vault.setManagementFee(0, {"from": gov})  # Just makes it easier later
    # Add strategies
    strategies = [gov.deploy(TestStrategy, vault) for _ in range(5)]
    for s in strategies:
        vault.addStrategy(s, 2_000, 0, 10 ** 21, 1000, {"from": gov})

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
    while vault.totalDebt() < vault.totalAssets():
        chain.sleep(1)
        for s in strategies:
            s.harvest({"from": gov})
        with brownie.reverts():
            vault.withdraw(5000, {"from": rando})

    # Everything is invested
    assert token.balanceOf(vault) == 0

    # One of our strategies suffers a loss
    total_assets = vault.totalAssets()
    loss = token.balanceOf(strategies[0]) // 2  # 10% of total
    vault.setStrategySetLimitRatio(strategies[0], 5000, 5000, {"from": gov})
    strategies[0]._takeFunds(loss, {"from": gov})
    # Harvest the loss
    assert vault.strategies(strategies[0]).dict()["totalLoss"] == 0

    # Throw if there is a loss on withdrawal, unless the user opts in
    assert token.balanceOf(vault) == 0
    with brownie.reverts():
        vault.withdraw({"from": rando})
    with brownie.reverts():
        vault.withdraw(1000, rando, 9999, {"from": rando})  # Opt-in to 99.99% loss

    chain.snapshot()  # For later

    # Scenario 1: we panic, and try to get out as quickly as possible (total loss)
    assert token.balanceOf(rando) == 0

    # User first try to withdraw with more than 100% losses, which is nonsensical
    with brownie.reverts():
        vault.withdraw(1000, rando, 10_001, {"from": rando})

    pricePerShareBefore = vault.pricePerShare()
    vault.withdraw(1000, rando, 10_000, {"from": rando})  # Opt-in to 100% loss
    assert vault.strategies(strategies[0]).dict()["totalLoss"] == 1000
    assert token.balanceOf(rando) == 0  # 100% loss (because we didn't wait!)
    assert pricePerShareBefore == vault.pricePerShare()

    chain.revert()  # Back before the withdrawal

    # Scenario 2: we wait, and only suffer a minor loss

    strategies[0].harvest({"from": gov})
    assert vault.strategies(strategies[0]).dict()["totalLoss"] == loss
    assert token.balanceOf(rando) == 0
    vault.withdraw({"from": rando})  # no need for opt-in now that loss is reported
    # much smaller loss (because we waited!)
    assert token.balanceOf(rando) == 900  # because of 10% total loss


def test_progressive_withdrawal(
    chain, token, gov, Vault, guardian, rewards, TestStrategy
):
    vault = guardian.deploy(Vault)
    vault.initialize(
        token,
        gov,
        rewards,
        token.symbol() + " yVault",
        "yv" + token.symbol(),
        guardian,
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})

    strategies = [gov.deploy(TestStrategy, vault) for _ in range(2)]
    for s in strategies:
        vault.addStrategy(s, 1000, 0, 10, 1000, {"from": gov})

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
    for s in strategies:
        s.harvest({"from": gov})
    assert token.balanceOf(vault) < vault.totalAssets()  # Some debt is in strategies

    # Trying to withdraw 0 shares. It should revert
    with brownie.reverts():
        vault.withdraw(0, {"from": gov})

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
        token,
        gov,
        rewards,
        token.symbol() + " yVault",
        "yv" + token.symbol(),
        guardian,
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})

    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 1000, 0, 10, 1000, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit(1000, {"from": gov})

    # Remove all tokens from gov to make asserts easier
    token.approve(gov, 2 ** 256 - 1, {"from": gov})
    token.transferFrom(gov, guardian, token.balanceOf(gov), {"from": gov})

    chain.sleep(8640)
    chain.sleep(1)
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
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


def test_withdrawal_with_reentrancy(
    chain, token, gov, Vault, guardian, rewards, TestStrategy
):
    vault = guardian.deploy(Vault)
    vault.initialize(
        token,
        gov,
        rewards,
        token.symbol() + " yVault",
        "yv" + token.symbol(),
        guardian,
    )

    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})

    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1000, {"from": gov})

    strategy._toggleReentrancyExploit()

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit(1000, {"from": gov})

    # move funds into strategy
    chain.sleep(1)  # Needs to be a second ahead, at least
    chain.sleep(1)
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    strategy.harvest({"from": gov})

    # To simulate reentrancy we need strategy to have some balance
    vault.transfer(strategy, vault.balanceOf(gov) // 2, {"from": gov})

    assert vault.balanceOf(strategy) > 0

    # given previous setup the withdraw should revert from reentrancy guard
    with brownie.reverts():
        vault.withdraw(vault.balanceOf(gov), {"from": gov})


def test_user_withdraw(chain, gov, token, vault, strategy, rando):
    # set fees to 0
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})

    vault.setLockedProfitDegradation(
        1e18, {"from": gov}
    )  # Set profit degradation to 1 sec.
    deposit = vault.totalAssets()
    pricePerShareBefore = vault.pricePerShare()
    token.transfer(strategy, vault.totalAssets(), {"from": gov})  # seed some profit
    chain.sleep(1)
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    strategy.harvest({"from": gov})

    chain.sleep(1)
    chain.mine(1)  # cant withdraw on same block

    assert vault.pricePerShare() == pricePerShareBefore * 2  # profit
    assert vault.totalAssets() == deposit * 2  # profit

    vault.withdraw({"from": gov})

    assert vault.totalSupply() == 0
    assert token.balanceOf(vault) == 0  # everything is withdrawn


def test_profit_degradation(chain, gov, token, vault, strategy, rando):
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})
    token.approve(vault, 2 ** 256 - 1, {"from": gov})

    deposit = vault.totalAssets()
    token.transfer(strategy, deposit, {"from": gov})  # seed some profit
    chain.sleep(1)
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    strategy.harvest({"from": gov})

    vault.withdraw({"from": gov})

    assert vault.totalSupply() == 0
    assert (
        token.balanceOf(vault) > 0
    )  # all money withdrawn but some profit left locked for 6 hours

    vault.deposit(deposit, {"from": gov})

    pricePerShareBefore = vault.pricePerShare()

    chain.sleep(1_000)
    chain.mine(1)

    assert vault.pricePerShare() > pricePerShareBefore

    # wait 6 hours. should be all profit now
    chain.sleep(21600)
    chain.mine(1)
    assert vault.pricePerShare() >= pricePerShareBefore * 2 * 0.99


def test_withdraw_partial_delegate_assets(chain, gov, token, vault, strategy, rando):
    # set fees to 0
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})

    vault.setLockedProfitDegradation(
        1e18, {"from": gov}
    )  # Set profit degradation to 1 sec.
    deposit = vault.totalAssets()
    pricePerShareBefore = vault.pricePerShare()
    token.transfer(strategy, vault.totalAssets(), {"from": gov})  # seed some profit
    chain.sleep(1)
    vault.setStrategyEnforceChangeLimit(strategy, False, {"from": gov})
    strategy.harvest({"from": gov})

    chain.sleep(1)
    chain.mine(1)  # cant withdraw on same block

    assert vault.pricePerShare() == pricePerShareBefore * 2  # profit
    assert vault.totalAssets() == deposit * 2  # profit

    # Check delegation math/logic
    strategy._toggleDelegation()
    assert strategy.delegatedAssets() == vault.strategies(strategy).dict()["totalDebt"]
    strategy_delegated_assets_before = strategy.delegatedAssets()

    # not all deposit is delegated
    assert vault.balanceOf(gov) >= strategy_delegated_assets_before

    # withdraw up to delegated assets a partial amount
    vault.withdraw(strategy_delegated_assets_before, {"from": gov})

    strategy_delegated_assets_after = strategy.delegatedAssets()
    assert (
        strategy_delegated_assets_after
        == vault.strategies(strategy).dict()["totalDebt"]
    )


def test_token_amount_does_not_change_on_deposit_withdrawal(
    web3, chain, gov, token, vault, strategy, rando
):
    # set fees to 0
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})
    vault.setLockedProfitDegradation(1e10, {"from": gov})
    # test is only valid if some profit are locked.
    chain.sleep(1)
    strategy.harvest()
    token.transfer(strategy, 100, {"from": gov})
    chain.sleep(1)
    strategy.harvest()
    assert vault.lockedProfit() == 100

    token.transfer(rando, 1000, {"from": gov})
    token.approve(vault, 1000, {"from": rando})
    balanceBefore = token.balanceOf(rando)
    web3.provider.make_request("miner_stop", [])

    deposit = vault.deposit(1000, {"from": rando, "required_confs": 0})
    withdraw = vault.withdraw({"from": rando, "required_confs": 0})

    # When ganache is started with automing this is the only way to get two transactions within the same block.
    web3.provider.make_request("evm_mine", [chain.time() + 5])
    web3.provider.make_request("miner_start", [])

    assert deposit.block_number == withdraw.block_number
    assert token.balanceOf(rando) == balanceBefore
