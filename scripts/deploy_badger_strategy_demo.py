"""
NOTE: THIS IS A DEMO
Real deployment is done in each brownie mix
"""
from pathlib import Path
import yaml
import click

from brownie import TestStrategyUpgradeable, AdminUpgradeabilityProxy, accounts, network, web3
from eth_utils import is_checksum_address
from semantic_version import Version

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent / "ethpm-config.yaml").read_text()
)["version"]

defaults = { # TODO: Use Badger on-chain Registry for all versions & defaults
    'vault': web3.toChecksumAddress("0x55949f769d0af7453881435612561d109fff07b8"),
    'stratLogic': web3.toChecksumAddress("0x0000000000000000000000000000000000000000"),
    'proxyAdmin': web3.toChecksumAddress("0xB10b3Af646Afadd9C62D663dd5d226B15C25CdFA"),
    'strategist': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'rewards': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'keeper': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
}

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
    """
    Deploy the strat logic
    """
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")

    click.echo(
        f"""
        Release Information

         local package version: {PACKAGE_VERSION}
        """
    )

    if click.confirm("Deploy Logic Contracts", default="Y"):
        use_existing_logic = False
    else:
        # use_existing_logic = True
        # strat_logic_address = get_address("Strat Logic Address", default=defaults['stratLogic'])
        use_existing_logic = False
        click.echo("Existing Vault Logic not supported, defaulting Deploy Logic Contracts to 'Yes'")

    vault = get_address("Strat Vault", default=defaults['vault'])
    proxyAdmin = get_address("Proxy Admin", default=defaults['proxyAdmin'])

    rewards = get_address("Rewards contract", default=defaults['rewards'])
    strategist = get_address("Strategist Address", default=defaults['strategist'])
    keeper = get_address("Keeper Address", default=defaults['keeper'])

    click.echo(
        f"""
    Strat Deployment Parameters

         use proxy: {True}
    target release: {PACKAGE_VERSION} # TODO: Use Badger Registry for all versions & defaults
              vault: '{vault}'
            proxyAdmin: '{proxyAdmin}'

            rewards: '{rewards}'
            strategist: '{strategist}'
            keeper: '{keeper}'
    """
    )

    if click.confirm("Deploy New Strategy"):
        args = [
            vault,
            strategist,
            rewards,
            keeper
        ]
        
        strat_logic = TestStrategyUpgradeable.deploy({'from': dev})
        strat_proxy = AdminUpgradeabilityProxy.deploy(strat_logic, proxyAdmin, strat_logic.initialize.encode_input(*args), {'from': dev})
        print(strat_proxy)
        print("Strat Args", args)
        click.echo(f"New Strategy Release deployed [{strat_proxy.address}]")
        click.echo(
            "    NOTE: Strategy is not registered in Registry, please register!"
        )
