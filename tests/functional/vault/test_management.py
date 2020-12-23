import pytest
import brownie


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture
def vault(gov, management, token, Vault):
    vault = gov.deploy(Vault, token, gov, gov, "", "")
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def strategy1(gov, vault, TestStrategy):
    yield gov.deploy(TestStrategy, vault)


@pytest.fixture
def strategy2(gov, vault, TestStrategy):
    yield gov.deploy(TestStrategy, vault)


@pytest.fixture
def test_withdrawalQueue(gov, management, vault, strategy1, strategy2):
    vault.addStrategy(strategy1, 10000, 10, 1000, {"from": gov})
    vault.addStrategy(strategy2, 10000, 10, 1000, {"from": gov})

    assert vault.withdrawalQueue(0) == strategy1
    assert vault.withdrawalQueue(1) == strategy2

    queue = [ZERO_ADDRESS] * 20
    queue[0] = strategy2
    queue[1] = strategy1
    vault.setWithdrawalQueue(queue, {"from": management})

    assert vault.withdrawalQueue(1) == strategy1
    assert vault.withdrawalQueue(0) == strategy2

    vault.removeStrategyFromQueue(strategy2, {"from": management})
    assert vault.withdrawalQueue(0) == strategy1
    assert vault.withdrawalQueue(1) == ZERO_ADDRESS

    vault.addStrategyToQueue(strategy2, {"from": management})
    assert vault.withdrawalQueue(0) == strategy1
    assert vault.withdrawalQueue(1) == strategy2


def test_strategy_limits(gov, management, vault, strategy1):
    vault.addStrategy(strategy1, 10000, 10, 1000, {"from": gov})

    vault.updateStrategyDebtLimit(strategy1, 50, {"from": management})
    assert vault.strategies(strategy1).dict()["debtLimit"] == 50

    vault.updateStrategyRateLimit(strategy1, 20, {"from": management})
    assert vault.strategies(strategy1).dict()["rateLimit"] == 20


def test_management_permission(management, vault, strategy1, strategy2):

    with brownie.reverts():
        vault.addStrategy(strategy1, 10000, 10, 1000, {"from": management})

    with brownie.reverts():
        vault.updateStrategyPerformanceFee(strategy1, 10, {"from": management})

    with brownie.reverts():
        vault.migrateStrategy(strategy1, strategy2, {"from": management})

    with brownie.reverts():
        vault.setDepositLimit(10, {"from": management})
