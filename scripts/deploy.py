from pathlib import Path
import yaml
import click

from brownie import Token, Vault, accounts, network, web3
from eth_utils import is_checksum_address


DEFAULT_VAULT_NAME = lambda token: f"{token.symbol()} yVault"
DEFAULT_VAULT_SYMBOL = lambda token: f"yv{token.symbol()}"

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent / "ethpm-config.yaml").read_text()
)["version"]


def get_address(msg: str, default: str = None) -> str:
    val = click.prompt(msg, default=default)

    # Keep asking user for click.prompt until it passes
    while True:

        if is_checksum_address(val):
            return val
        elif addr := web3.ens.address(val):
            click.echo(f"Found ENS '{val}' [{addr}]")
            return addr

        click.echo(
            f"I'm sorry, but '{val}' is not a checksummed address or valid ENS record"
        )
        # NOTE: Only display default once
        val = click.prompt(msg)


def main():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")

    token = Token.at(get_address("ERC20 Token"))
    gov = get_address("Yearn Governance", default="ychad.eth")
    rewards = get_address(
        "Rewards contract", default="0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde"
    )
    name = click.prompt(f"Set description", default=DEFAULT_VAULT_NAME(token))
    symbol = click.prompt(f"Set symbol", default=DEFAULT_VAULT_SYMBOL(token))

    click.echo(
        f"""
    Vault Parameters

   version: {PACKAGE_VERSION}
     token: {token.address}
  governer: {gov}
   rewards: {rewards}
      name: '{name}'
    symbol: '{symbol}'
    """
    )

    if click.confirm("Deploy New Vault"):
        vault = dev.deploy(
            Vault,
            token,
            gov,
            rewards,
            # NOTE: Empty string `""` means no override (don't use click default tho)
            name if name != DEFAULT_VAULT_NAME(token) else "",
            symbol if symbol != DEFAULT_VAULT_SYMBOL(token) else "",
        )
