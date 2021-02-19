import pytest

from semantic_version import Version

from brownie import yToken, AffiliateToken, Vault
from brownie.test import strategy


class Migration:
    st_ratio = strategy("decimal", min_value="0.1", max_value="0.9")
    st_index = strategy("uint256")

    def __init__(
        self,
        registry,
        token,
        create_vault,
        wrapper,
        user,
        initial_vault,
        balance_check_fn,
    ):
        self.registry = registry
        self.token = token
        self.create_vault = lambda s, t, v: create_vault(token=t, version=v)
        self.wrapper = wrapper
        self.user = user
        self._initial_vault = initial_vault
        self.balance_check_fn = balance_check_fn

    def setup(self):
        self.vaults = [self._initial_vault]

    def rule_new_release(self):
        api_version = str(Version(self.registry.latestRelease()).next_major())
        vault = self.create_vault(self.token, api_version)
        print(f"  Registry.newRelease({vault})")
        self.registry.newRelease(vault, {"from": self.user})
        self.vaults.append(vault)

    def rule_deposit(self, ratio="st_ratio"):
        amount = int(ratio * self.wrapper.balanceOf(self.user))
        if amount > 0:
            print(f"  Wrapper.deposit({amount})")
            self.wrapper.deposit(amount)

        else:
            print("  Wrapper.deposit: Nothing to deposit...")

    def rule_harvest(self, index="st_index"):
        # Give some profit to one of the Vaults we are invested in
        vaults_in_use = [v for v in self.vaults if v.totalSupply() > 0]
        if len(vaults_in_use) > 0:
            vault = vaults_in_use[index % len(self.vaults)]
            print(f"  {vault}.harvest()")
            self.token.transfer(vault, int(1e17))

        else:
            print("  vaults.harvest: No Vaults in use...")

    def rule_migrate(self):
        print("  Wrapper.migrate()")
        self.wrapper.migrate()

    def rule_withdraw(self, ratio="st_ratio"):
        amount = int(ratio * self.wrapper.balanceOf(self.user))
        if amount > 0:
            print(f"  Wrapper.withdraw({amount})")
            self.wrapper.withdraw(amount)

        else:
            print("  Wrapper.withdraw: Nothing to withdraw...")

    def invariant_balances(self):
        assert self.balance_check_fn()


@pytest.mark.parametrize("Wrapper", [yToken, AffiliateToken])
def test_migration_wrapper(state_machine, token, create_vault, gov, registry, Wrapper):
    starting_balance = token.balanceOf(gov)

    if Wrapper._name == "yToken":
        wrapper = gov.deploy(Wrapper, token)
        vault_balance = lambda self: sum(
            int(v.balanceOf(gov) * v.pricePerShare() / 10 ** v.decimals())
            for v in self.vaults
        )
        balance_check_fn = lambda vaults: (
            token.balanceOf(gov) + vault_balance(vaults) == starting_balance
        )

    else:
        wrapper = gov.deploy(Wrapper, token, "Test Affiliate Token", "afToken")
        balance_check_fn = lambda self: (
            int(
                wrapper.balanceOf(gov)
                * wrapper.pricePerShare()
                / 10 ** wrapper.decimals()
            )
            + token.balanceOf(gov)
            == starting_balance
        )

    # NOTE: Need to seed registry with at least one vault to function
    vault = create_vault(token=token, version="1.0.0")
    registry.newRelease(vault, {"from": gov})

    state_machine(
        Migration, registry, token, create_vault, wrapper, gov, vault, balance_check_fn,
    )
