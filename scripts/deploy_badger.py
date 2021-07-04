from pathlib import Path
import yaml
import click

from brownie import Token, Vault, AdminUpgradeabilityProxy, Registry, accounts, network, web3
from eth_utils import is_checksum_address
from semantic_version import Version


DEFAULT_VAULT_NAME = lambda token: f"Badger Sett {token.symbol()}"
DEFAULT_VAULT_SYMBOL = lambda token: f"b{token.symbol()}"

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent / "ethpm-config.yaml").read_text()
)["version"]

defaults = { # TODO: Use Badger on-chain Registry for all versions & defaults
    'governance': web3.toChecksumAddress("0x55949f769d0af7453881435612561d109fff07b8"),
    'strategist': web3.toChecksumAddress("0x55949f769d0af7453881435612561d109fff07b8"),
    'rewards': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'keeper': web3.toChecksumAddress("0x872213E29C85d7e30F1C8202FC47eD1Ec124BB1D"),
    'guardian': web3.toChecksumAddress("0x29F7F8896Fb913CF7f9949C623F896a154727919"),
    'proxyAdmin': web3.toChecksumAddress("0xB10b3Af646Afadd9C62D663dd5d226B15C25CdFA"),
    'vaultLogic': web3.toChecksumAddress("0x0000000000000000000000000000000000000000")
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
    Deploy the vault logic
    Deploy the strat logic

    Deploy the vault proxy
    Init the vault proxy

    Deploy the strat proxy
    Init the strat proxy
    """
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
\
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
        # vault_logic_address = get_address("Vault Logic Address", default=defaults['vaultLogic'])
        use_existing_logic = False
        click.echo("Existing Vault Logic not supported, defaulting Deploy Logic Contracts to 'Yes'")

    token = Token.at(get_address("Vault Want Token"))

    gov = get_address("Vault Governance", default=defaults['governance'])
    rewards = get_address("Rewards contract", default=defaults['rewards'])
    guardian = get_address("Vault Guardian", default=defaults['guardian'])
    management = get_address("Vault Management", default=defaults['governance'])
    proxyAdmin = get_address("Proxy Admin", default=defaults['proxyAdmin'])

    name = click.prompt(f"Set description", default=DEFAULT_VAULT_NAME(token))
    symbol = click.prompt(f"Set symbol", default=DEFAULT_VAULT_SYMBOL(token))

    click.echo(
        f"""
    Vault Deployment Parameters

         use proxy: {True}
    target release: {PACKAGE_VERSION} # TODO: Use Badger Registry for all versions & defaults
     token address: {token.address}
      token symbol: {DEFAULT_VAULT_SYMBOL(token)}
        governance: {gov}
        management: {management}
           rewards: {rewards}
          guardian: {guardian}
              name: '{name}'
            symbol: '{symbol}'
            proxy admin: {proxyAdmin}
    """
    )

    if click.confirm("Deploy New Vault"):
        args = [
            token,
            gov,
            rewards,
            # NOTE: Empty string `""` means no override (don't use click default tho)
            name if name != DEFAULT_VAULT_NAME(token) else "",
            symbol if symbol != DEFAULT_VAULT_SYMBOL(token) else "",
            guardian,
            management
        ]
        
        vault_logic = Vault.deploy({'from': dev})
        vault_proxy = AdminUpgradeabilityProxy.deploy(vault_logic, proxyAdmin, vault_logic.initialize.encode_input(*args), {'from': dev})
        print(vault_proxy)
        print("Vault Args", args)
        click.echo(f"New Vault Release deployed [{vault_proxy.address}]")
        click.echo(
            "    NOTE: Vault is not registered in Registry, please register!"
        )
