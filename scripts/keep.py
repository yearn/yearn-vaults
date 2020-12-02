from brownie import accounts, network, interface, Vault, Token
from brownie.network.gas.strategies import GasNowScalingStrategy
from decimal import Decimal
from eth_utils import is_checksum_address
import requests
from time import sleep


GAS_BUFFER = 1.2

gas_strategy = GasNowScalingStrategy()


def get_address(msg: str) -> str:
    while True:
        addr = input(msg)
        if is_checksum_address(addr):
            return addr
        print(f"I'm sorry, but '{addr}' is not a checksummed address")


def main():
    print(f"You are using the '{network.show_active()}' network")
    bot = accounts.load("bot")
    print(f"You are using: 'bot' [{bot.address}]")
    # TODO: Allow adding/removing strategies during operation
    strategies = [interface.StrategyAPI(get_address("Strategy to farm: "))]
    while input("Add another strategy? (y/[N]): ").lower() == "y":
        strategies.append(interface.StrategyAPI(get_address("Strategy to farm: ")))

    vault = Vault.at(strategies[0].vault())
    want = Token.at(vault.token())

    for strategy in strategies:
        assert (
            strategy.keeper() == bot.address
        ), "Bot is not set as keeper! [{strategy.address}]"
        assert (
            strategy.vault() == vault.address
        ), f"Vault mismatch! [{strategy.address}]"

    while True:
        starting_balance = bot.balance()

        calls_made = 0
        total_gas_estimate = 0
        for strategy in strategies:
            # Display some relevant statistics
            symbol = want.symbol()
            credit = vault.creditAvailable(strategy) / 10 ** vault.decimals()
            print(f"[{strategy.address}] Credit Available: {credit:0.3f} {symbol}")
            debt = vault.debtOutstanding(strategy) / 10 ** vault.decimals()
            print(f"[{strategy.address}] Debt Outstanding: {debt:0.3f} {symbol}")

            starting_gas_price = next(gas_strategy.get_gas_price())

            try:
                tend_gas_estimate = int(
                    GAS_BUFFER * strategy.tend.estimate_gas({"from": bot})
                )
                total_gas_estimate += tend_gas_estimate
            except ValueError:
                print(f"[{strategy.address}] `tend` estimate fails")
                tend_gas_estimate = None

            try:
                harvest_gas_estimate = int(
                    GAS_BUFFER * strategy.harvest.estimate_gas({"from": bot})
                )
                total_gas_estimate += harvest_gas_estimate
            except ValueError:
                print(f"[{strategy.address}] `harvest` estimate fails")
                harvest_gas_estimate = None

            if harvest_gas_estimate and strategy.harvestTrigger(
                harvest_gas_estimate * starting_gas_price
            ):
                try:
                    strategy.harvest({"from": bot, "gas_price": gas_strategy})
                    calls_made += 1
                except:
                    print(f"[{strategy.address}] `harvest` call fails")

            elif tend_gas_estimate and strategy.tendTrigger(
                tend_gas_estimate * starting_gas_price
            ):
                try:
                    strategy.tend({"from": bot, "gas_price": gas_strategy})
                    calls_made += 1
                except:
                    print(f"[{strategy.address}] `tend` call fails")

        # Check running 10 `tend`s & `harvest`s per strategy at estimated gas price
        # would empty the balance of the bot account
        if bot.balance() < 10 * total_gas_estimate * starting_gas_price:
            print(f"Need more ether please! {bot.address}")

        # Wait a minute if we didn't make any calls
        if calls_made > 0:
            gas_cost = (starting_balance - bot.balance()) / 10 ** 18
            num_harvests = bot.balance() // (starting_balance - bot.balance())
            print(f"Made {calls_made} calls, spent {gas_cost} ETH on gas.")
            print(
                f"At this rate, it'll take {num_harvests} harvests to run out of gas."
            )
        else:
            print("Sleeping for 60 seconds...")
            sleep(60)
