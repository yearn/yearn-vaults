import brownie


def test_withdraw(chain, gov, token, vault, strategy, rando):
    token.approve(vault, token.balanceOf(gov), {"from": gov})
    vault.deposit(token.balanceOf(gov) // 2, {"from": gov})
    chain.sleep(8640)
    chain.sleep(1)
    strategy.harvest({"from": gov})  # Seed some debt in there
    assert strategy.estimatedTotalAssets() > 0

    balance = strategy.estimatedTotalAssets()
    strategy.withdraw(balance // 2, {"from": vault.address})
    # NOTE: This may be +1 more than just dividing it
    assert strategy.estimatedTotalAssets() == balance - balance // 2

    # Not just anyone can call it
    with brownie.reverts():
        strategy.withdraw(balance // 2, {"from": rando})

    # Anything over what we can liquidate is totally withdrawn
    strategy.withdraw(balance, {"from": vault.address})
    assert strategy.estimatedTotalAssets() == 0
