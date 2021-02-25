import pytest
import brownie
from brownie import ZERO_ADDRESS


@pytest.fixture
def other_token(gov, Token):
    yield gov.deploy(Token)


@pytest.fixture
def other_vault(gov, Vault, other_token):
    vault = gov.deploy(Vault)
    vault.initialize(other_token, gov, gov, "", "", gov)
    yield vault


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
):

    tx = strategy.clone(other_vault, {"from": rando})
    address = tx.events["Cloned"]["clone"]
    new_strategy = TestStrategy.at(address)

    assert new_strategy.strategist() == rando
    assert new_strategy.rewards() == rando
    assert new_strategy.keeper() == rando
    assert Token.at(new_strategy.want()).name() == "yearn.finance test token"

    # Test the other clone method with all params
    tx = strategy.clone(other_vault, gov, guardian, strategist, {"from": rando})
    address = tx.events["Cloned"]["clone"]
    new_strategy = TestStrategy.at(address)

    assert new_strategy.strategist() == gov
    assert new_strategy.rewards() == guardian
    assert new_strategy.keeper() == strategist


def test_double_initialize(TestStrategy, vault, other_vault, gov):
    strategy = gov.deploy(TestStrategy, vault)

    # Sholdn't be able to initialize twice
    with brownie.reverts():
        strategy.initialize(other_vault, gov, gov, gov)
