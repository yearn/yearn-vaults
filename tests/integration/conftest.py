import pytest


@pytest.fixture
def andre(accounts):
    # Andre, giver of tokens, and maker of yield
    yield accounts[0]


@pytest.fixture
def create_token(andre, Token):
    yield lambda: andre.deploy(Token, 18)


@pytest.fixture
def token(create_token):
    yield create_token()


@pytest.fixture
def gov(accounts):
    # yearn multis... I mean YFI governance. I swear!
    yield accounts[1]


@pytest.fixture
def registry(gov, Registry):
    yield gov.deploy(Registry)


@pytest.fixture
def common_health_check(gov, CommonHealthCheck):
    yield gov.deploy(CommonHealthCheck)


@pytest.fixture
def rewards(gov):
    yield gov  # TODO: Add rewards contract


@pytest.fixture
def guardian(accounts):
    # YFI Whale, probably
    yield accounts[2]


@pytest.fixture
def create_vault(
    gov, rewards, guardian, create_token, patch_vault_version, common_health_check
):
    def create_vault(token=None, version=None):
        if token is None:
            token = create_token()
        vault = patch_vault_version(version).deploy({"from": guardian})
        vault.initialize(
            token,
            gov,
            rewards,
            token.symbol() + " yVault",
            "yv" + token.symbol(),
            guardian,
            guardian,
            common_health_check,
        )
        vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
        assert vault.depositLimit() == 2 ** 256 - 1
        assert vault.token() == token
        return vault

    yield create_vault


@pytest.fixture
def vault(token, create_vault):
    yield create_vault(token)


@pytest.fixture
def strategist(accounts):
    # You! Our new Strategist!
    yield accounts[3]


@pytest.fixture
def keeper(accounts):
    # This is our trusty bot!
    yield accounts[4]


@pytest.fixture
def strategy(gov, strategist, keeper, vault, TestStrategy):
    strategy = strategist.deploy(TestStrategy, vault)
    strategy.setKeeper(keeper)
    yield strategy


@pytest.fixture
def nocoiner(accounts):
    # Has no tokens (DeFi is a ponzi scheme!)
    yield accounts[5]


@pytest.fixture
def pleb(accounts, andre, token, vault):
    # Small fish in a big pond
    a = accounts[6]
    # Has 0.01% of tokens (heard about this new DeFi thing!)
    bal = token.totalSupply() // 10000
    token.transfer(a, bal, {"from": andre})
    # Unlimited Approvals
    token.approve(vault, 2 ** 256 - 1, {"from": a})
    # Deposit half their stack
    vault.deposit(bal // 2, {"from": a})
    yield a


@pytest.fixture
def chad(accounts, andre, token, vault):
    # Just here to have fun!
    a = accounts[7]
    # Has 0.1% of tokens (somehow makes money trying every new thing)
    bal = token.totalSupply() // 1000
    token.transfer(a, bal, {"from": andre})
    # Unlimited Approvals
    token.approve(vault, 2 ** 256 - 1, {"from": a})
    # Deposit half their stack
    vault.deposit(bal // 2, {"from": a})
    yield a


@pytest.fixture
def greyhat(accounts, andre, token, vault):
    # Chaotic evil, will eat you alive
    a = accounts[8]
    # Has 1% of tokens (earned them the *hard way*)
    bal = token.totalSupply() // 100
    token.transfer(a, bal, {"from": andre})
    # Unlimited Approvals
    token.approve(vault, 2 ** 256 - 1, {"from": a})
    # Deposit half their stack
    vault.deposit(bal // 2, {"from": a})
    yield a


@pytest.fixture
def whale(accounts, andre, token, vault):
    # Totally in it for the tech
    a = accounts[9]
    # Has 10% of tokens (was in the ICO)
    bal = token.totalSupply() // 10
    token.transfer(a, bal, {"from": andre})
    # Unlimited Approvals
    token.approve(vault, 2 ** 256 - 1, {"from": a})
    # Deposit half their stack
    vault.deposit(bal // 2, {"from": a})
    yield a
