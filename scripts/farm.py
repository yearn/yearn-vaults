from brownie import accounts, network, interface
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
    strategy = interface.StrategyAPI(get_address("Strategy to farm: "))

    assert strategy.keeper() == bot.address, "Bot is not set as keeper!"

    while True:

        gas_price = get_gas_price()
        starting_balance = bot.balance()
        if strategy.tendTrigger(40000 * gas_price):
            strategy.tend({"from": bot, "gas_price": gas_price})
            print(f"`tend()` [{starting_balance - bot.balance()} wei]")

        elif strategy.harvestTrigger(120000 * gas_price):
            strategy.harvest({"from": bot, "gas_price": gas_price})
            print(f"`harvest()` [{starting_balance - bot.balance()} wei]")

        sleep(60)
