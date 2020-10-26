import pytest


@pytest.fixture
def gov(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def token(gov, Token):
    yield gov.deploy(Token)


@pytest.fixture
def vault(gov, guardian, token, rewards, Vault):
    vault = guardian.deploy(Vault, token, gov, rewards, "", "")
    # Make it so vault has some AUM to start
    token.approve(vault, token.balanceOf(gov) // 2, {"from": gov})
    vault.deposit(token.balanceOf(gov) // 2, {"from": gov})
    assert token.balanceOf(vault) == token.balanceOf(gov)
    assert vault.totalDebt() == 0  # No connected strategies yet
    yield vault


@pytest.fixture
def strategist(accounts):
    yield accounts[3]


@pytest.fixture
def keeper(accounts):
    yield accounts[4]


@pytest.fixture
def strategy(gov, strategist, keeper, token, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)
    strategy.setKeeper(keeper, {"from": strategist})
    vault.addStrategy(
        strategy,
        token.totalSupply() // 5,  # Debt limit of 20% of token supply (40% of Vault)
        token.totalSupply() // 1000,  # Rate limt of 0.1% of token supply per block
        50,  # 0.5% performance fee for Strategist
        {"from": gov},
    )
    yield strategy


@pytest.fixture
def rando(accounts):
    yield accounts[9]
