from pathlib import Path
import yaml

from brownie import Token, Vault, accounts, network, web3
from eth_utils import is_checksum_address

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent / "ethpm-config.yaml").read_text()
)["version"]


def get_address(msg: str) -> str:
    while True:
        val = input(msg)
        if is_checksum_address(val):
            return val
        else:
            addr = web3.ens.address(val)
            if addr:
                print(f"Found ENS '{val}' [{addr}]")
                return addr
        print(f"I'm sorry, but '{val}' is not a checksummed address or ENS")


def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load("dev")
    print(f"You are using: 'dev' [{dev.address}]")
    token = Token.at(get_address("ERC20 Token: "))
    gov = get_address("Yearn Governance: ")
    rewards = get_address("Rewards contract: ")
    name = input(f"Set description ['yearn {token.name()}']: ") or ""
    symbol = input(f"Set symbol ['y{token.symbol()}']: ") or ""
    print(
        f"""
    Vault Parameters

   version: {PACKAGE_VERSION}
     token: {token.address}
  governer: {gov}
   rewards: {rewards}
      name: '{name or 'yearn ' + token.name()}'
    symbol: '{symbol or 'y' + token.symbol()}'
    """
    )
    if input("Deploy New Vault? y/[N]: ").lower() != "y":
        return
    print("Deploying Vault...")
    vault = dev.deploy(Vault, token, gov, rewards, name, symbol)
