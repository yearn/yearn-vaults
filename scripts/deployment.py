from brownie import Vault, accounts, network
from eth_utils import is_checksum_address


def get_address(msg: str) -> str:
    while True:
        addr = input(msg)
        if is_checksum_address(addr):
            return addr
        print(f"I'm sorry, but '{addr}' is not a checksummed address")


def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load("dev")
    print(f"You are using: 'dev' [{dev.address}]")
    token = get_address("ERC20 Token: ")
    gov = get_address("yEarn Governance: ")
    rewards = get_address("Rewards contract: ")
    print("Deploying Vault...")
    vault = dev.deploy(Vault, token, gov, rewards)
