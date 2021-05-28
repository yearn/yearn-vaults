import pytest

from brownie import Token, TokenNoReturn


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
def create_token(gov):
    def create_token(decimal=18, behaviour="Normal"):
        assert behaviour in ("Normal", "NoReturn")
        return gov.deploy(Token if behaviour == "Normal" else TokenNoReturn, decimal)

    yield create_token


@pytest.fixture(params=[("Normal", 18), ("NoReturn", 18), ("Normal", 8), ("Normal", 2)])
def token(create_token, request):
    # NOTE: Run our test suite using both compliant and non-compliant ERC20 Token
    (behaviour, decimal) = request.param
    yield create_token(decimal=decimal, behaviour=behaviour)


@pytest.fixture
def create_vault(gov, guardian, rewards, create_token, patch_vault_version):
    def create_vault(token=None, version=None, governance=gov):
        if token is None:
            token = create_token()
        vault = patch_vault_version(version).deploy({"from": guardian})
        vault.initialize(token, governance, rewards, "", "", guardian, governance)
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


@pytest.fixture(params=["RegularStrategy", "ClonedStrategy"])
def strategy(gov, strategist, keeper, rewards, vault, TestStrategy, request):
    strategy = strategist.deploy(TestStrategy, vault)

    if request.param == "ClonedStrategy":
        # deploy the proxy using as logic the original strategy
        tx = strategy.clone(vault, strategist, rewards, keeper, {"from": strategist})
        # strategy proxy address is returned in the event `Cloned`
        strategyAddress = tx.events["Cloned"]["clone"]
        # redefine strategy as the new proxy deployed
        strategy = TestStrategy.at(strategyAddress, owner=strategist)

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
    yield gov.deploy(Registry)
