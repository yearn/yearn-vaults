class NormalOperation:
    def __init__(self, token, vault, strategy, gov, mint, keeper):
        self.token = token
        self.vault = vault
        self.gov = gov
        self.mint = mint
        self.keeper = keeper
        self.strategy = strategy

    def setup(self):
        self.current_return = lambda: self.token.balanceOf(self.strategy) // 1000  # 0.1% return, every time
        self.last_price = 0.0
        self.returns = 0

    def rule_harvest(self):
        c = self.vault.creditAvailable(self.strategy)
        er = self.vault.expectedReturn(self.strategy)
        r = self.current_return()
        dl = self.vault.estimateAdjustedDebtLimit(r, self.strategy)
        print(
            f"""
    Available Credit: {c}
    Expected Return: {er}
    Actual Return: {r}
    Adjusted Debt: {dl}"""
        )
        self.token.transfer(self.strategy, r, {"from": self.mint})
        self.strategy.harvest({"from": self.keeper})

    def invariant_accounting(self):
        assert self.vault.totalDebt() == self.token.balanceOf(self.strategy)
        assert self.vault.totalAssets() == sum(self.token.balanceOf(i) for i in (self.vault, self.strategy))

    def invariant_numbergoup(self):
        # Positive-return Strategy should never reduce the price of a share
        price = self.vault.pricePerShare() / 10 ** self.vault.decimals() if self.vault.totalSupply() > 0 else 0.0
        assert price >= self.last_price
        self.last_price = price


def test_normal_operation(gov, strategy, vault, token, andre, keeper, state_machine):
    vault.addStrategy(
        strategy,
        token.balanceOf(vault) // 2,  # Go up to 50% of Vault AUM
        token.balanceOf(vault) // 1000,  # 0.1% of Vault AUM per block
        {"from": gov},
    )
    state_machine(NormalOperation, token, vault, strategy, gov, andre, keeper)
