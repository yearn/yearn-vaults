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
def management(accounts):
    yield accounts[3]


@pytest.fixture
def create_token(gov, Token):
    def create_token():
        return Token.deploy({"from": gov})

    yield create_token


# NOTE: Only apply check for working with non-compliant tokens in tests
#       that work directly with the Vault
@pytest.fixture(params=["Normal", "NoReturn"])
def token(create_token, request):
    token = create_token()
    # NOTE: Run our test suite using both compliant and non-compliant ERC20 Token
    if request.param == "NoReturn":
        token._initialized = False  # otherwise Brownie throws an `AttributeError`
        setattr(token, "transfer", token.transferWithoutReturn)
        setattr(token, "transferFrom", token.transferFromWithoutReturn)
        token._initialized = True  # shhh, nothing to see here...
    yield token


@pytest.fixture
def create_vault(gov, guardian, rewards, create_token, patch_vault_version):
    def create_vault(token=None, version=None, governance=gov):
        if token is None:
            token = create_token()
        vault = patch_vault_version(version).deploy({"from": guardian})
        vault.initialize(token, governance, rewards, "", "", guardian)
        vault.setDepositLimit(2 ** 256 - 1, {"from": governance})
        return vault

    yield create_vault


@pytest.fixture
def vault(gov, management, token, create_vault):
    vault = create_vault(token=token, governance=gov)
    vault.setManagement(management, {"from": gov})
    # Make it so vault has some AUM to start
    token.approve(vault, token.balanceOf(gov) // 2, {"from": gov})
    vault.deposit(token.balanceOf(gov) // 2, {"from": gov})
    yield vault


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def strategy(gov, strategist, keeper, token, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)
    strategy.setKeeper(keeper, {"from": strategist})
    vault.addStrategy(
        strategy,
        4_000,  # 40% of Vault
        0,  # Minimum debt increase per harvest
        2 ** 256 - 1,  # maximum debt increase per harvest
        1000,  # 10% performance fee for Strategist
        {"from": gov},
    )
    yield strategy


@pytest.fixture
def rando(accounts):
    yield accounts[9]


@pytest.fixture
def registry(gov, Registry):
    yield Registry.deploy({"from": gov})
