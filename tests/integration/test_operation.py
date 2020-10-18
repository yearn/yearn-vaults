class NormalOperation:
    def __init__(self, web3, token, vault, strategy, user, farm, keeper):
        self.web3 = web3
        self.token = token
        self.vault = vault
        self.strategy = strategy
        self.farm = farm
        self.keeper = keeper
        self.user = user

    def rule_deposit(self):
        print("  Vault.deposit()")

        # Deposit 50% of what they have left
        amt = self.token.balanceOf(self.user) // 2
        self.vault.deposit(amt, {"from": self.user})

    def rule_withdraw(self):
        print("  Vault.withdraw()")

        # Withdraw 50% of what they have in the Vault
        amt = self.vault.balanceOf(self.user) // 2
        self.vault.withdraw(amt, {"from": self.user})

    def rule_harvest(self):
        print("  Strategy.harvest()")

        # Earn 1% yield on deposits in some farming protocol
        amt = self.token.balanceOf(self.strategy) // 100
        self.token.transfer(self.strategy, amt, {"from": self.farm})

        # Keeper decides to harvest the yield
        self.strategy.harvest({"from": self.keeper})

    # TODO: Invariant that user did not get > they should have
    # TODO: Invariant that fees/accounting is all perfect
    # TODO: Invariant that all economic assumptions are maintained


def test_normal_operation(
    web3, gov, strategy, vault, token, chad, andre, keeper, state_machine
):
    vault.addStrategy(
        strategy,
        token.balanceOf(vault),  # Go up to 100% of Vault AUM
        token.balanceOf(vault),  # 100% of Vault AUM per block (no rate limit)
        50,  # 0.5% performance fee for Strategist
        {"from": gov},
    )
    strategy.harvest({"from": keeper})
    assert token.balanceOf(vault) == 0
    state_machine(NormalOperation, web3, token, vault, strategy, chad, andre, keeper)
