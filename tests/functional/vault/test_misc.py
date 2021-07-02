import pytest
import brownie
import pytest

MAX_UINT256 = 2 ** 256 - 1
MAX_BPS = 10000


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token, 18)


@pytest.fixture
def token_false_return(gov, TokenFalseReturn):
    yield gov.deploy(TokenFalseReturn, 18)


@pytest.fixture
def vault(gov, management, token, Vault):
    # NOTE: Because the fixture has tokens in it already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov, gov
    )
    vault.setDepositLimit(MAX_UINT256, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def other_vault(gov, Vault, other_token):
    vault = gov.deploy(Vault)
    vault.initialize(other_token, gov, gov, "", "", gov, gov)
    yield vault


@pytest.fixture
def vault_with_false_returning_token(gov, Vault, token_false_return):
    vault = gov.deploy(Vault)
    vault.initialize(token_false_return, gov, gov, "", "", gov)
    vault.setDepositLimit(MAX_UINT256, {"from": gov})
    yield vault


def test_credit_available_minDebtPerHarvest_larger_than_available(
    Vault, TestStrategy, token, gov
):
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov, gov
    )
    vault.setDepositLimit(MAX_UINT256, {"from": gov})
    strategy = gov.deploy(TestStrategy, vault)
    vault.addStrategy(
        strategy,
        10000,  # 100% of Vault AUM
        0,  # minDebtPerHarvest
        MAX_UINT256,  # maxDebtPerHarvest
        0,  # performanceFee
        {"from": gov},
    )

    token.approve(vault, MAX_UINT256, {"from": gov})
    vault.deposit(500, {"from": gov})
    vault_debtLimit = vault.debtRatio() * vault.totalAssets() / MAX_BPS
    vault_totalDebt = vault.totalDebt()
    strategy_debtRatio = vault.strategies(strategy).dict()["debtRatio"]
    strategy_debtLimit = strategy_debtRatio * vault.totalAssets()
    strategy_totalDebt = vault.strategies(strategy).dict()["totalDebt"]

    # Exhausted credit line
    strategyDebtExceedsLimit = strategy_totalDebt >= strategy_debtLimit
    vaultDebtExceedsLimit = vault_totalDebt >= vault_debtLimit
    exhaustedCreditLine = vaultDebtExceedsLimit or strategyDebtExceedsLimit
    assert not exhaustedCreditLine

    # Start with debt limit left for the Strategy
    available = strategy_debtLimit - strategy_totalDebt

    # Adjust by the global debt limit left
    available = min(available, vault_debtLimit - vault_totalDebt)

    # Can only borrow up to what the contract has in reserve
    available = min(available, token.balanceOf(vault))

    vault.updateStrategyMinDebtPerHarvest(strategy, available + 1, {"from": gov})
    strategy_minDebtPerHarvest = vault.strategies(strategy).dict()["minDebtPerHarvest"]
    minDebtPerHarvestExceedsAvailable = strategy_minDebtPerHarvest > available
    assert minDebtPerHarvestExceedsAvailable

    creditAvalable = vault.creditAvailable(strategy)
    assert creditAvalable == 0


def test_regular_available_deposit_limit(Vault, token, gov):
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    token.approve(vault, 100, {"from": gov})
    vault.setDepositLimit(100)

    vault.deposit(50, {"from": gov})
    assert vault.availableDepositLimit() == 50

    vault.deposit(50, {"from": gov})
    assert vault.availableDepositLimit() == 0


def test_negative_available_deposit_limit(Vault, token, gov):
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    token.approve(vault, 100, {"from": gov})
    vault.setDepositLimit(100)

    vault.deposit(100, {"from": gov})
    assert vault.availableDepositLimit() == 0

    vault.setDepositLimit(50)
    assert vault.availableDepositLimit() == 0


def test_sweep(gov, vault, rando, token, other_token):
    token.transfer(vault, token.balanceOf(gov), {"from": gov})
    other_token.transfer(vault, other_token.balanceOf(gov), {"from": gov})

    # Vault wrapped token doesn't work
    assert token.address == vault.token()
    assert token.balanceOf(vault) > 0
    with brownie.reverts():
        vault.sweep(token, {"from": gov})

    # But any other random token works
    assert other_token.address != vault.token()
    assert other_token.balanceOf(vault) > 0
    assert other_token.balanceOf(gov) == 0
    # Not any random person can do this
    with brownie.reverts():
        vault.sweep(other_token, {"from": rando})

    before = other_token.balanceOf(vault)
    vault.sweep(other_token, 1, {"from": gov})
    assert other_token.balanceOf(vault) == before - 1
    assert other_token.balanceOf(gov) == 1
    vault.sweep(other_token, {"from": gov})
    assert other_token.balanceOf(vault) == 0
    assert other_token.balanceOf(gov) == before
    assert other_token.balanceOf(rando) == 0


def test_reject_ether(gov, vault):
    # These functions should reject any calls with value
    for func, args in [
        ("setGovernance", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setManagement", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("acceptGovernance", []),
        ("setRewards", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setGuardian", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("setPerformanceFee", [0]),
        ("setManagementFee", [0]),
        ("setEmergencyShutdown", [True]),
        ("approve", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
        ("transfer", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
        (
            "transferFrom",
            [
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                1,
            ],
        ),
        ("deposit", []),
        ("withdraw", []),
        ("deposit", [1]),
        ("withdraw", [1]),
        ("deposit", [1, "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("withdraw", [1, "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("addStrategy", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1, 1, 1, 1]),
        ("addStrategyToQueue", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("removeStrategyFromQueue", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("updateStrategyDebtRatio", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
        (
            "updateStrategyMinDebtPerHarvest",
            ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1],
        ),
        (
            "updateStrategyMaxDebtPerHarvest",
            ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1],
        ),
        (
            "updateStrategyPerformanceFee",
            ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1],
        ),
        (
            "migrateStrategy",
            [
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            ],
        ),
        ("revokeStrategy", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("report", [1, 2, 3]),
        ("sweep", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"]),
        ("sweep", ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 1]),
    ]:
        with brownie.reverts():
            # NOTE: gov can do anything
            getattr(vault, func)(*args, {"from": gov, "value": 1})

    # Fallback fails too
    with brownie.reverts():
        gov.transfer(vault, 1)

    # NOTE: Just for coverage
    with brownie.reverts():
        gov.transfer(vault, 0)


def test_deposit_withdraw_faillure(token, gov, vault):
    token._setBlocked(vault.address, True, {"from": gov})
    with brownie.reverts():
        vault.deposit({"from": gov})

    token._setBlocked(vault.address, False, {"from": gov})
    token.approve(vault, MAX_UINT256, {"from": gov})
    vault.deposit({"from": gov})
    token._setBlocked(gov, True, {"from": gov})

    with brownie.reverts():
        vault.withdraw(vault.balanceOf(gov), {"from": gov})


def test_sandwich_attack(
    chain, TestStrategy, web3, token, gov, vault, strategist, rando
):

    honest_lp = gov
    attacker = rando
    balance = token.balanceOf(honest_lp) / 2

    # seed attacker their funds
    token.transfer(attacker, balance, {"from": honest_lp})

    # we don't use the one in conftest because we want no rate limit
    strategy = strategist.deploy(TestStrategy, vault)
    vault.setManagementFee(0, {"from": gov})
    vault.setPerformanceFee(0, {"from": gov})
    vault.addStrategy(strategy, 4_000, 0, MAX_UINT256, 0, {"from": gov})
    vault.updateStrategyPerformanceFee(strategy, 0, {"from": gov})

    chain.sleep(1)
    strategy.harvest({"from": strategist})
    # strategy is returning 0.02%. Equivalent to 35.6% a year at 5 harvests a day
    profit_to_be_returned = token.balanceOf(strategy) / 5000
    token.transfer(strategy, profit_to_be_returned, {"from": honest_lp})

    # now for the attack

    # attacker sees harvest enter tx pool
    attack_amount = token.balanceOf(attacker)

    # attacker deposits
    token.approve(vault, attack_amount, {"from": attacker})
    vault.deposit(attack_amount, {"from": attacker})

    # harvest happens
    chain.sleep(1)
    strategy.harvest({"from": strategist})

    chain.sleep(1)
    chain.mine(1)

    # attacker withdraws. Pays back loan. and keeps or sells profit
    vault.withdraw(vault.balanceOf(attacker), {"from": attacker})

    profit = token.balanceOf(attacker) - attack_amount
    profit_percent = profit / attack_amount

    print(f"Attack Profit Percent: {profit_percent}")
    # 5 rebases a day = 1780 a year. Less than 0.0004% profit on attack makes it closer to neutral EV
    assert profit_percent == pytest.approx(0, abs=10e-5)


def test_erc20_safe_transfer(gov, other_vault, token, other_token, token_false_return):
    # Normal ERC-20 tokens (and tokens with no return) can be swept if the vault has sweepable tokens
    token.transfer(other_vault, token.balanceOf(gov) // 2, {"from": gov})
    vaultBalanceOf = other_token.balanceOf(other_vault)
    sweepAmount = vaultBalanceOf
    other_vault.sweep(token, sweepAmount, {"from": gov})

    # Tokens that return false should revert (erc20_safe_transfer failed)
    with brownie.reverts():
        other_vault.sweep(token_false_return, 0, {"from": gov})


def test_erc20_safe_transferFrom(
    gov, token, vault, token_false_return, vault_with_false_returning_token
):
    # Vaults with false returning tokens
    with brownie.reverts():
        token_false_return.approve(
            vault_with_false_returning_token, MAX_UINT256, {"from": gov}
        )
        vault_with_false_returning_token.deposit(5000, {"from": gov})

    # Normal ERC-20 vault deposits (via erc20_safe_transferFrom) should work
    token.approve(vault, MAX_UINT256, {"from": gov})
    vault.deposit(5000, {"from": gov})
