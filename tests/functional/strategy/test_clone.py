import pytest
import brownie
from brownie import ZERO_ADDRESS
from eth_abi import encode_abi


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token, 18)


@pytest.fixture
def other_vault(gov, Vault, other_token):
    vault = gov.deploy(Vault)
    vault.initialize(other_token, gov, gov, "", "", gov, gov)
    yield vault


@pytest.fixture
def strategy(gov, strategist, keeper, rewards, vault, TestStrategy):
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


def test_clone(
    Token,
    token,
    other_token,
    strategy,
    vault,
    other_vault,
    gov,
    strategist,
    guardian,
    TestStrategy,
    rando,
    strategyVersionRegistry,
):
    params = encode_abi(
        ["address", "address", "address", "address"],
        [other_vault.address, gov.address, guardian.address, strategist.address],
    )
    tx = strategyVersionRegistry.clone(strategy, params, {"from": rando})
    address = tx.events["Cloned"]["clone"]
    new_strategy = TestStrategy.at(address)

    assert new_strategy.isOriginal() == False
    with brownie.reverts():
        strategyVersionRegistry.clone(new_strategy, params, {"from": rando})

    assert new_strategy.strategist() == gov
    assert new_strategy.rewards() == guardian
    assert new_strategy.keeper() == strategist

    # test state variables have been initialized with default (hardcoded) values
    assert new_strategy.minReportDelay() == 0
    assert new_strategy.maxReportDelay() == 86400
    assert new_strategy.profitFactor() == 100
    assert new_strategy.debtThreshold() == 0
