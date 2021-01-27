import brownie


def test_withdraw(chain, gov, token, vault, strategy, rando):
    token.approve(vault, token.balanceOf(gov), {"from": gov})
    vault.deposit(token.balanceOf(gov) // 2, {"from": gov})
    chain.sleep(8640)
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

def test_user_withdraw(chain, gov, token, vault, strategy, rando):
    #set fees to 0
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})

    vault.setLockedProfitDegration(1e18, {"from": gov})
    deposit = vault.totalAssets()
    pricePerShareBefore = vault.pricePerShare()
    token.transfer(strategy, vault.totalAssets(), {"from": gov}) # seed some profit
    strategy.harvest({"from": gov})

    chain.sleep(1)
    chain.mine(1) # cant withdraw on same block

    assert vault.pricePerShare() == pricePerShareBefore*2 # profit
    assert vault.totalAssets() == deposit*2 # profit

    vault.withdraw({"from": gov})

    assert vault.totalSupply() == 0
    assert token.balanceOf(vault) == 0 # all money withdrawn but some profit left

def test_profit_degration(chain, gov, token, vault, strategy, rando):
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})
    token.approve(vault,2 ** 256 - 1, {"from": gov})

    deposit = vault.totalAssets()
    token.transfer(strategy, deposit, {"from": gov}) # seed some profit

    strategy.harvest({"from": gov})
    
    vault.withdraw({"from": gov})

    assert vault.totalSupply() == 0
    assert token.balanceOf(vault) > 0 # all money withdrawn but some profit left

    vault.deposit(deposit, {"from": gov})

    pricePerShareBefore = vault.pricePerShare()

    chain.sleep(10)
    chain.mine(1)
    
    assert vault.pricePerShare() > pricePerShareBefore

    #wait 6 hours. should be all profit now
    chain.sleep(21600)
    chain.mine(1)
    assert vault.pricePerShare() >= pricePerShareBefore*2 * 0.99
