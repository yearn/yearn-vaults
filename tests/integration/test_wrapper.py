import pytest

from collections import namedtuple
from semantic_version import Version

from brownie import yToken, AffiliateToken, Vault
from brownie.test import strategy


class Migration:
    st_ratio = strategy("decimal", min_value="0.1", max_value="0.9")
    st_index = strategy("uint256")

    def __init__(
        self, chain, registry, token, create_vault, wrapper, first_vault, user, gov
    ):
        self.chain = chain
        self.registry = registry
        self.token = token
        # NOTE: Have to fakeout this call because it thinks it's a method
        self.create_vault = lambda self, version: create_vault(
            token=token, version=version
        )
        self.wrapper = wrapper
        self.user = user
        self.gov = gov
        self.vaults = []
        self._first_vault = first_vault
        self.starting_balance = token.balanceOf(user)  # Don't touch!

    def setup(self):
        # NOTE: Approve wrapper for all future deposits (only once)
        self.token.approve(self.wrapper, 2 ** 256 - 1, {"from": self.user})

        # NOTE: Deposit a little bit to start (so we don't just always skip)
        self.wrapper.deposit(self.starting_balance // 10, {"from": self.user})
        self.vaults = [self._first_vault]

    def rule_new_release(self):
        next_version = str(Version(self.registry.latestRelease()).next_major())
        vault = self.create_vault(next_version)
        print(f"  Registry.newRelease({vault})")

        self.registry.newRelease(vault, {"from": self.gov})
        self.registry.endorseVault(vault, {"from": self.gov})

        # NOTE: yToken's are non-custodial, so you need to authorize them
        if self.wrapper._name == "yToken":
            vault.approve(self.wrapper, 2 ** 256 - 1, {"from": self.user})

        self.vaults.append(vault)

    def rule_deposit(self, ratio="st_ratio"):
        amount = int(ratio * self.token.balanceOf(self.user))
        if amount > 0:
            print(f"  Wrapper.deposit({amount})")
            self.wrapper.deposit(amount, {"from": self.user})

        else:
            print("  Wrapper.deposit: Nothing to deposit...")

    def rule_harvest(self, index="st_index"):
        # Give some profit to one of the Vaults we are invested in
        vaults_in_use = [v for v in self.vaults if v.totalSupply() > 0]
        if len(vaults_in_use) > 0:
            vault = vaults_in_use[index % len(vaults_in_use)]
            amount = int(1e17)
            print(f"  {vault}.harvest({amount})")
            # TODO: fix with AirdropStrategy
            self.token.transfer(vault, amount, {"from": self.user})
            # NOTE: Wait enough time where "profit locking" isn't a problem (about a day)
            self.chain.mine(timedelta=24 * 60 * 60)

        else:
            print("  vaults.harvest: No Vaults in use...")

    def rule_migrate(self):
        print("  Wrapper.migrate()")
        self.wrapper.migrate({"from": self.gov})

    def rule_withdraw(self, ratio="st_ratio"):
        amount = int(ratio * self.wrapper.balanceOf(self.user))
        if amount > 0:
            print(f"  Wrapper.withdraw({amount})")
            self.wrapper.withdraw(amount, {"from": self.user}).return_value

        else:
            print("  Wrapper.withdraw: Nothing to withdraw...")

    def invariant_balances(self):
        actual_deposits = sum(v.totalAssets() for v in self.vaults)
        expected_deposits = self.starting_balance - self.token.balanceOf(self.user)
        assert actual_deposits == expected_deposits


@pytest.mark.parametrize("Wrapper", (AffiliateToken, yToken))
def test_migration_wrapper(
    chain, state_machine, token, create_vault, whale, gov, registry, Wrapper
):
    if Wrapper._name == "AffiliateToken":
        wrapper = gov.deploy(
            Wrapper, token, registry, "Test Affiliate Token", "afToken"
        )
    else:
        wrapper = gov.deploy(Wrapper, token, registry)

    # NOTE: Must start with at least one vault in registry (for token)
    vault = create_vault(token=token, version="1.0.0")
    registry.newRelease(vault, {"from": gov})
    registry.endorseVault(vault, {"from": gov})

    # NOTE: yToken's are non-custodial, so you need to authorize them
    if wrapper._name == "yToken":
        vault.approve(wrapper, 2 ** 256 - 1, {"from": whale})

    state_machine(
        Migration, chain, registry, token, create_vault, wrapper, vault, whale, gov
    )
