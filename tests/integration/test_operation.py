class NormalOperation:
    def __init__(self, token, vault, strategy, user, farm, keeper):
        self.token = token
        self.vault = vault
        self.strategy = strategy
        self.farm = farm
        self.keeper = keeper
        self.user = user

    def setup(self):
        self.last_price = 1.0

    def rule_deposit(self):
        print("  NormalOperation.deposit()")
        # Deposit 50% of what they have left
        self.vault.deposit(self.token.balanceOf(self.user) // 2, {"from": self.user})

    def rule_withdraw(self):
        print("  NormalOperation.withdraw()")
        # Withdraw 50% of what they have in the Vault
        self.vault.withdraw(self.vault.balanceOf(self.user) // 2, {"from": self.user})

    def rule_yield(self):
        print("  NormalOperation.yield()")
        # Earn 1% yield on deposits in some farming protocol
        self.token.transfer(
            self.strategy,
            self.token.balanceOf(self.strategy) // 100,
            {"from": self.farm},
        )

    def rule_harvest(self):
        print("  NormalOperation.harvest()")
        # Keeper decides to harvest the yield
        self.strategy.harvest({"from": self.keeper})

    def invariant_numbergoup(self):
        # Positive-return Strategy should never reduce the price of a share
        price = self.vault.pricePerShare() / 10 ** self.vault.decimals()
        assert price >= self.last_price
        self.last_price = price


def test_normal_operation(
    gov, strategy, vault, token, chad, andre, keeper, state_machine
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
    state_machine(NormalOperation, token, vault, strategy, chad, andre, keeper)
