from brownie import Wei, reverts
import brownie


def test_sandwich_attack(TestStrategy, web3, token, gov, vault, strategist, rando):

    honest_lp = gov
    attacker = rando
    balance = token.balanceOf(honest_lp) / 2

    # seed attacker their funds. Same amount as deposited in vault
    token.transfer(attacker, balance, {"from": honest_lp})
    bv = print(token.balanceOf(vault) / 1e18)
    vault.withdraw(vault.balanceOf(honest_lp) / 2, {"from": honest_lp})
    bv = print(token.balanceOf(vault) / 1e18)

    # our actors:
    # attacker is attacker
    # strategist is vault owner
    # honest_lp is a normal lp

    # ------ setup vault ------
    # we don't use the one in conf because we want no rate limit
    strategy = strategist.deploy(TestStrategy, vault)
    vault.addStrategy(
        strategy, token.totalSupply(), token.totalSupply(), 50, {"from": gov}
    )

    strategy.harvest({"from": strategist})
    strategy_expected_return = token.balanceOf(honest_lp) / 1000
    token.transfer(strategy, strategy_expected_return, {"from": honest_lp})

    # now for the attack

    # attacker sees harvest enter tx pool
    attack_amount = balance

    # attacker deposits
    token.approve(vault, attack_amount, {"from": attacker})
    vault.deposit(attack_amount, {"from": attacker})

    # harvest happens
    strategy.harvest({"from": strategist})

    # attacker withdraws. Pays back loan. and keeps or sells profit
    vault.withdraw(vault.balanceOf(attacker), {"from": attacker})

    profit = token.balanceOf(attacker) - attack_amount
    profit_percent = profit / strategy_expected_return
    # print("attacker profit from attack = ", profit / 1e18)
    # print("attacker profit share = ", (token.balanceOf(attacker)) / attack_amount)
    # print("attacker percent of harvest = ", "{:.2%}".format(profit_percent))
    # print("honest_lp share = ", vault.pricePerShare() / 1e18)
    # profit percent should be less than 5%
    assert profit_percent < 0.05
