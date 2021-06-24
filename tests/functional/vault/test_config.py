from pathlib import Path
import yaml

import pytest
import brownie

from brownie import ZERO_ADDRESS

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent.parent.parent / "ethpm-config.yaml").read_text()
)["version"]


DEGRADATION_COEFFICIENT = 10 ** 18


def test_api_adherrance(check_api_adherrance, Vault, interface):
    check_api_adherrance(Vault, interface.VaultAPI)


def test_vault_deployment(guardian, gov, rewards, token, Vault):
    # Deploy the Vault without any name/symbol overrides
    vault = guardian.deploy(Vault)
    vault.initialize(
        token,
        gov,
        rewards,
        token.symbol() + " yVault",
        "yv" + token.symbol(),
        guardian,
    )
    # Addresses
    assert vault.governance() == gov
    assert vault.management() == guardian
    assert vault.guardian() == guardian
    assert vault.rewards() == rewards
    assert vault.token() == token
    # UI Stuff
    assert vault.name() == token.symbol() + " yVault"
    assert vault.symbol() == "yv" + token.symbol()
    assert vault.decimals() == token.decimals()
    assert vault.apiVersion() == PACKAGE_VERSION

    assert vault.debtRatio() == 0
    assert vault.depositLimit() == 0
    assert vault.creditAvailable() == 0
    assert vault.debtOutstanding() == 0
    assert vault.maxAvailableShares() == 0
    assert vault.totalAssets() == 0
    assert vault.pricePerShare() / (10 ** vault.decimals()) == 1.0


def test_vault_name_symbol_override(guardian, gov, rewards, token, Vault):
    # Deploy the Vault with name/symbol overrides
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "crvY yVault", "yvcrvY", guardian)
    # Assert that the overrides worked
    assert vault.name() == "crvY yVault"
    assert vault.symbol() == "yvcrvY"


def test_vault_reinitialization(guardian, gov, rewards, token, Vault):
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "crvY yVault", "yvcrvY", guardian)
    # Can't reinitialize a vault
    with brownie.reverts():
        vault.initialize(token, gov, rewards, "crvY yVault", "yvcrvY", guardian)


@pytest.mark.parametrize(
    "getter,setter,val,guard_allowed",
    [
        ("name", "setName", "NewName yVault", False),
        ("symbol", "setSymbol", "yvNEW", False),
        ("emergencyShutdown", "setEmergencyShutdown", True, True),
        ("emergencyShutdown", "setEmergencyShutdown", False, False),
        ("guardian", "setGuardian", None, True),
        ("rewards", "setRewards", None, False),
        ("lockedProfitDegradation", "setLockedProfitDegradation", 1000, False),
        ("management", "setManagement", None, False),
        ("performanceFee", "setPerformanceFee", 1000, False),
        ("managementFee", "setManagementFee", 1000, False),
        ("depositLimit", "setDepositLimit", 1000, False),
    ],
)
def test_vault_setParams(
    chain,
    gov,
    guardian,
    management,
    vault,
    rando,
    getter,
    setter,
    val,
    guard_allowed,
):
    if val is None:
        # Can't access fixtures, so use None to mean any random address
        val = rando

    # rando shouldn't be able to call these methods
    with brownie.reverts():
        getattr(vault, setter)(val, {"from": rando})

    if guard_allowed:
        getattr(vault, setter)(val, {"from": guardian})
        assert getattr(vault, getter)() == val
        chain.undo()
    else:
        with brownie.reverts():
            getattr(vault, setter)(val, {"from": guardian})

    # Management is never allowed
    with brownie.reverts():
        getattr(vault, setter)(val, {"from": management})

    # gov is always allowed
    getattr(vault, setter)(val, {"from": gov})
    assert getattr(vault, getter)() == val


@pytest.mark.parametrize(
    "key,setter,val,max",
    [
        ("debtRatio", "updateStrategyDebtRatio", 500, 10000),
        ("minDebtPerHarvest", "updateStrategyMinDebtPerHarvest", 10, None),
        ("maxDebtPerHarvest", "updateStrategyMaxDebtPerHarvest", 10, None),
    ],
)
def test_vault_updateStrategy(
    chain, gov, guardian, management, vault, strategy, rando, key, setter, val, max
):

    # rando shouldn't be able to call these methods
    with brownie.reverts():
        getattr(vault, setter)(strategy, val, {"from": rando})

    # guardian is never allowed
    with brownie.reverts():
        getattr(vault, setter)(strategy, val, {"from": guardian})

    # management is always allowed
    getattr(vault, setter)(strategy, val, {"from": management})
    assert vault.strategies(strategy).dict()[key] == val

    chain.undo()  # Revert previous setting
    assert vault.strategies(strategy).dict()[key] != val

    # gov is always allowed
    getattr(vault, setter)(strategy, val, {"from": gov})
    assert vault.strategies(strategy).dict()[key] == val

    if max:
        # Can't set it more than max
        getattr(vault, setter)(strategy, max, {"from": gov})
        assert vault.strategies(strategy).dict()[key] == max
        with brownie.reverts():
            getattr(vault, setter)(strategy, max + 1, {"from": gov})
        assert vault.strategies(strategy).dict()[key] == max


def test_min_max_debtIncrease(gov, vault, TestStrategy):
    strategy = gov.deploy(TestStrategy, vault)
    # Can't set min > max or max < min in adding a strategy
    with brownie.reverts():
        vault.addStrategy(strategy, 1_000, 20_000, 10_000, 1_000, {"from": gov})

    vault.addStrategy(strategy, 1_000, 10_000, 10_000, 1_000, {"from": gov})
    # Can't set min > max
    with brownie.reverts():
        vault.updateStrategyMaxDebtPerHarvest(
            strategy,
            vault.strategies(strategy).dict()["minDebtPerHarvest"] - 1,
            {"from": gov},
        )
    # Can't set max > min
    with brownie.reverts():
        vault.updateStrategyMinDebtPerHarvest(
            strategy,
            vault.strategies(strategy).dict()["maxDebtPerHarvest"] + 1,
            {"from": gov},
        )


def test_vault_setGovernance(gov, vault, rando):
    newGov = rando
    # No one can set governance but governance
    with brownie.reverts():
        vault.setGovernance(newGov, {"from": newGov})
    # Governance doesn't change until it's accepted
    vault.setGovernance(newGov, {"from": gov})
    assert vault.governance() == gov
    # Only new governance can accept a change of governance
    with brownie.reverts():
        vault.acceptGovernance({"from": gov})
    # Governance doesn't change until it's accepted
    vault.acceptGovernance({"from": newGov})
    assert vault.governance() == newGov
    # No one can set governance but governance
    with brownie.reverts():
        vault.setGovernance(newGov, {"from": gov})
    # Only new governance can accept a change of governance
    with brownie.reverts():
        vault.acceptGovernance({"from": gov})


def test_vault_setLockedProfitDegradation_range(gov, vault):
    # value must be between 0 and DEGRADATION_COEFFICIENT (inclusive)
    vault.setLockedProfitDegradation(0, {"from": gov})
    vault.setLockedProfitDegradation(DEGRADATION_COEFFICIENT, {"from": gov})
    with brownie.reverts():
        vault.setLockedProfitDegradation(DEGRADATION_COEFFICIENT + 1, {"from": gov})


def test_vault_setParams_bad_vals(gov, vault):
    with brownie.reverts():
        vault.setRewards(ZERO_ADDRESS, {"from": gov})

    with brownie.reverts():
        vault.setRewards(vault, {"from": gov})
