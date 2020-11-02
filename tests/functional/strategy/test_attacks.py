from brownie import Wei, reverts
import brownie


def test_sandwich_attack(TestStrategy, web3, token, gov, vault, strategist, rando):

    honest_lp = gov
    attacker = rando
    balance = token.balanceOf(honest_lp) / 2

    # seed attacker their funds
    token.transfer(attacker, balance, {"from": honest_lp})

    # we don't use the one in conftest because we want no rate limit
    strategy = strategist.deploy(TestStrategy, vault)
    vault.addStrategy(strategy, 2 ** 256 - 1, 2 ** 256 - 1, 50, {"from": gov})

    strategy.harvest({"from": strategist})
    # strategy is returning 0.02%. Equivalent to 35.6% a year at 5 harvests a day
    profit_to_be_returned = token.balanceOf(strategy) / 5000
    token.transfer(strategy, profit_to_be_returned, {"from": honest_lp})

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
    profit_percent = profit / attack_amount
    # 5 rebases a day = 1780 a year. 0.004% profit a rebase is 7.12% a year return
    assert profit_percent < 0.00004
