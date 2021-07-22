import pytest
import brownie
from eth_abi import encode_abi


@pytest.fixture
def strategy(
    strategist,
    vault,
    TestStrategy,
):
    yield strategist.deploy(TestStrategy, vault)


def test_set_governance(gov, strategist, rando, strategyVersionRegistry):
    with brownie.reverts():
        strategyVersionRegistry.setGovernance(strategist, {"from": rando})

    strategyVersionRegistry.setGovernance(strategist, {"from": gov})
    strategyVersionRegistry.acceptGovernance({"from": strategist})


def test_add_new_release(gov, strategy, rando, strategyVersionRegistry):
    with brownie.reverts():
        strategyVersionRegistry.setGovernance(strategy, {"from": rando})

    strategyVersionRegistry.addNewRelease(strategy, {"from": gov})
    assert strategy.address == strategyVersionRegistry.latestRelease(
        strategy.name(), strategy.apiVersion()
    )

    strategyVersionRegistry.addNewRelease(strategy, "name", {"from": gov})
    assert strategy.address == strategyVersionRegistry.latestRelease(
        "name", strategy.apiVersion()
    )


def test_clone(gov, strategy, vault, strategyVersionRegistry):
    with brownie.reverts():
        strategyVersionRegistry.clone(strategy, params)

    strategyVersionRegistry.addNewRelease(strategy, {"from": gov})

    params = encode_abi(
        ["address", "address", "address", "address"],
        [vault.address, gov.address, gov.address, gov.address],
    )
    tx = strategyVersionRegistry.clone(strategy, params)
    clonedStrategy = tx.events["Cloned"]["clone"]

    with brownie.reverts():
        strategyVersionRegistry.addNewRelease(clonedStrategy, {"from": gov})

    with brownie.reverts():
        strategyVersionRegistry.clone(clonedStrategy, params, {"from": gov})
