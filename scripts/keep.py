from brownie import accounts, network, interface, Vault
from decimal import Decimal
from eth_utils import is_checksum_address
import requests
from time import sleep


def get_address(msg: str) -> str:
    while True:
        addr = input(msg)
        if is_checksum_address(addr):
            return addr
        print(f"I'm sorry, but '{addr}' is not a checksummed address")


def get_gas_price(confirmation_speed: str = "fast"):
    if "mainnet" not in network.show_active():
        return 10 ** 9  # 1 gwei
    data = requests.get("https://www.gasnow.org/api/v3/gas/price").json()
    return data["data"][confirmation_speed]


def main():
    print(f"You are using the '{network.show_active()}' network")
    bot = accounts.load("bot")
    print(f"You are using: 'bot' [{bot.address}]")
    # TODO: Manage a list of strategies
    # TODO: Allow adding/removing strategies during operation
    strategy = interface.StrategyAPI(get_address("Strategy to farm: "))

    assert strategy.keeper() == bot.address, "Bot is not set as keeper!"

    vault = Vault.at(strategy.vault())

    while True:
        # Display some relevant statistics
        credit = vault.creditAvailable(strategy) / 10 ** vault.decimals()
        print(f"Credit Available: {credit} {vault.symbol()[1:]}")

        gas_price = get_gas_price()
        starting_balance = bot.balance()
        # TODO: Actually estimate gas
        if strategy.tendTrigger(40000 * gas_price):
            print(f"tending... [{strategy.address}]")
            strategy.tend({"from": bot, "gas_price": gas_price})
            print(f"`tend()` [{starting_balance - bot.balance()} wei]")

        elif strategy.harvestTrigger(180000 * gas_price):
            print(f"harvesting... [{strategy.address}]")
            strategy.harvest({"from": bot, "gas_price": gas_price})
            print(f"`harvest()` [{starting_balance - bot.balance()} wei]")

        else:
            print("Sleeping for 60 seconds...")
            sleep(60)

        if bot.balance() < 10 ** 8 * gas_price:
            # Less than 100m gas left to spend
            print(f"Need more ether please! {bot.address}")
