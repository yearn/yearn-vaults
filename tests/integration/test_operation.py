class NormalOperation:
    def __init__(self, web3, token, vault, strategy, user, farm, keeper, chain):
        self.web3 = web3
        self.token = token
        self.vault = vault
        self.strategy = strategy
        self.farm = farm
        self.keeper = keeper
        self.user = user
        self.chain = chain

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
        self.chain.sleep(1)
        self.strategy.harvest({"from": self.keeper})

    # TODO: Invariant that user did not get > they should have
    # TODO: Invariant that fees/accounting is all perfect
    # TODO: Invariant that all economic assumptions are maintained


def test_normal_operation(
    web3, chain, gov, strategy, vault, token, chad, andre, keeper, state_machine
):
    vault.addStrategy(
        strategy,
        10_000,  # 100% of Vault AUM
        0,
        2 ** 256 - 1,  # no rate limit
        1000,  # 10% performance fee for Strategist
        {"from": gov},
    )
    chain.sleep(1)
    strategy.harvest({"from": keeper})
    assert token.balanceOf(vault) == 0
    state_machine(
        NormalOperation, web3, token, vault, strategy, chad, andre, keeper, chain
    )
