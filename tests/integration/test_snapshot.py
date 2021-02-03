import brownie
from brownie.test import strategy


class SnapshotHistory:

    st_accounts = strategy("address")
    st_decimals = strategy("decimal", min_value="0.1", max_value="0.9")

    def __init__(self, chain, accounts, token, vault):
        self.chain = chain
        self.accounts = accounts
        self.token = token
        self.vault = vault

        # Some setup checks
        balance = token.balanceOf(accounts[0])
        assert balance > 0
        # NOTE: Redistribute some wealth so test is interesting
        [token.transfer(a, balance // 10, {"from": accounts[0]}) for a in accounts[1:]]
        # NOTE: Assume Vault starts with no deposits
        assert max(vault.balanceOf(a) for a in accounts) == 0

    def setup(self):
        self.balance_history = [{a: 0 for a in self.accounts}] * len(self.chain)

    def initialize(self, ratio="st_decimals"):
        # Have everyone deposit some amount
        for a in self.accounts:
            self.rule_deposit(a, ratio)

    def record_balances(self):
        self.balance_history.append({a: self.vault.balanceOf(a) for a in self.accounts})

    def rule_nothing(self):
        print("No action")
        self.chain.mine()
        self.record_balances()

    def rule_deposit(self, a="st_accounts", ratio="st_decimals"):
        amt = int(self.token.balanceOf(a) * ratio)
        print(f"Vault.deposit({amt}, from={a})")

        self.token.approve(self.vault, amt, {"from": a})
        self.record_balances()

        if amt > 0:
            self.vault.deposit(amt, {"from": a})

        else:
            with brownie.reverts():
                self.vault.deposit(amt, {"from": a})

        self.record_balances()

    def rule_transfer(self, a="st_accounts", b="st_accounts", ratio="st_decimals"):
        amt = int(self.vault.balanceOf(a) * ratio)
        print(f"Vault.transfer({b}, {amt}, from={a})")

        self.vault.transfer(b, amt, {"from": a})
        self.record_balances()

    def rule_transferFrom(
        self, a="st_accounts", b="st_accounts", c="st_accounts", ratio="st_decimals",
    ):
        amt = int(self.vault.balanceOf(a) * ratio)
        print(f"Vault.transferFrom({a}, {b}, {amt}, from={c})")

        self.vault.approve(c, amt, {"from": a})
        self.record_balances()

        self.vault.transferFrom(a, b, amt, {"from": c})
        self.record_balances()

    def rule_withdraw(self, a="st_accounts", ratio="st_decimals"):
        amt = int(self.vault.balanceOf(a) * ratio)
        print(f"Vault.withdraw({amt}, from={a})")

        self.vault.withdraw(amt, {"from": a})
        self.record_balances()

    def invariant_balance_balance_history(self):
        for blk in range(len(self.chain)):
            balance_history = self.balance_history[blk]
            assert sum(balance_history.values()) == self.vault.totalSupplyAt(blk)

            for acct, balance in balance_history.items():
                assert self.vault.balanceOfAt(acct, blk) == balance


def test_snapshots(chain, accounts, token, vault, state_machine):
    state_machine(
        SnapshotHistory, chain, accounts, token, vault,
    )
