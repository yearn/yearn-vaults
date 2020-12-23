from pathlib import Path
import yaml

import pytest
import brownie


PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent.parent.parent / "ethpm-config.yaml").read_text()
)["version"]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def test_vault_deployment(guardian, gov, rewards, token, Vault):
    # Deploy the Vault without any name/symbol overrides
    vault = guardian.deploy(Vault, token, gov, rewards, "", "")
    # Addresses
    assert vault.governance() == gov
    assert vault.management() == gov
    assert vault.guardian() == guardian
    assert vault.rewards() == rewards
    assert vault.token() == token
    # UI Stuff
    assert vault.name() == token.symbol() + " yVault"
    assert vault.symbol() == "yv" + token.symbol()
    assert vault.decimals() == token.decimals()
    assert vault.apiVersion() == PACKAGE_VERSION

    assert vault.debtLimit() == 0
    assert vault.depositLimit() == 2 ** 256 - 1
    assert vault.creditAvailable() == 0
    assert vault.debtOutstanding() == 0
    assert vault.maxAvailableShares() == 0
    assert vault.totalAssets() == 0
    assert vault.pricePerShare() / (10 ** vault.decimals()) == 1.0


def test_vault_name_symbol_override(guardian, gov, rewards, token, Vault):
    # Deploy the Vault with name/symbol overrides
    vault = guardian.deploy(Vault, token, gov, rewards, "crvY yVault", "yvcrvY")
    # Assert that the overrides worked
    assert vault.name() == "crvY yVault"
    assert vault.symbol() == "yvcrvY"


@pytest.mark.parametrize(
    "getter,setter,val,gov_allowed,mgmt_allowed,guard_allowed",
    [
        ("name", "setName", "NewName yVault", True, False, False),
        ("symbol", "setSymbol", "yvNEW", True, False, False),
        ("emergencyShutdown", "setEmergencyShutdown", True, True, False, True),
        ("guardian", "setGuardian", None, True, False, True),
        ("rewards", "setRewards", None, True, False, False),
        ("management", "setManagement", None, True, False, False),
        ("performanceFee", "setPerformanceFee", 1000, True, False, False),
        ("managementFee", "setManagementFee", 1000, True, False, False),
        ("depositLimit", "setDepositLimit", 1000, True, False, False),
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
    gov_allowed,
    mgmt_allowed,
    guard_allowed,
):
    if not val:
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

    if mgmt_allowed:
        getattr(vault, setter)(val, {"from": management})
        assert getattr(vault, getter)() == val
        chain.undo()
    else:
        with brownie.reverts():
            getattr(vault, setter)(val, {"from": management})

    getattr(vault, setter)(val, {"from": gov})
    assert getattr(vault, getter)() == val


@pytest.mark.parametrize(
    "key,setter,val,gov_allowed,mgmt_allowed,guard_allowed",
    [
        ("debtLimit", "updateStrategyDebtLimit", 500, True, True, False),
        ("rateLimit", "updateStrategyRateLimit", 10, True, True, False),
    ],
)
def test_vault_updateStrategy(
    chain,
    gov,
    guardian,
    management,
    vault,
    strategy,
    rando,
    key,
    setter,
    val,
    gov_allowed,
    mgmt_allowed,
    guard_allowed,
):

    # rando shouldn't be able to call these methods
    with brownie.reverts():
        getattr(vault, setter)(strategy, val, {"from": rando})

    if guard_allowed:
        getattr(vault, setter)(strategy, val, {"from": guardian})
        assert vault.strategies(strategy).dict()[key] == val
        chain.undo()
    else:
        with brownie.reverts():
            getattr(vault, setter)(strategy, val, {"from": guardian})

    if mgmt_allowed:
        getattr(vault, setter)(strategy, val, {"from": management})
        assert vault.strategies(strategy).dict()[key] == val
        chain.undo()
    else:
        with brownie.reverts():
            getattr(vault, setter)(strategy, val, {"from": management})

    getattr(vault, setter)(strategy, val, {"from": gov})
    assert vault.strategies(strategy).dict()[key] == val


@pytest.mark.parametrize(
    "count,setter,gov_allowed,mgmt_allowed,guard_allowed",
    [
        (20, "setWithdrawalQueue", True, True, False),
        (0, "removeStrategyFromQueue", True, True, False),
        (1, "addStrategyToQueue", True, True, False),
    ],
)
def test_vault_withdrawalQueue(
    chain,
    gov,
    guardian,
    management,
    vault,
    strategy,
    rando,
    count,
    setter,
    gov_allowed,
    mgmt_allowed,
    guard_allowed,
):
    val = None
    if setter == "removeStrategyFromQueue":
        val = vault.withdrawalQueue(0)
    elif setter == "addStrategyToQueue":
        val = vault.withdrawalQueue(0)
        vault.removeStrategyFromQueue(val, {"from": gov})
    elif setter == "setWithdrawalQueue":
        val = [vault.withdrawalQueue(0)] * 20

    # rando shouldn't be able to call these methods
    with brownie.reverts():
        getattr(vault, setter)(val, {"from": rando})

    if guard_allowed:
        getattr(vault, setter)(val, {"from": guardian})
        assert strategies_len(vault) == count
        chain.undo()
    else:
        with brownie.reverts():
            getattr(vault, setter)(val, {"from": guardian})

    if mgmt_allowed:
        getattr(vault, setter)(val, {"from": management})
        assert strategies_len(vault) == count
        chain.undo()
    else:
        with brownie.reverts():
            getattr(vault, setter)(val, {"from": management})

    getattr(vault, setter)(val, {"from": gov})
    assert strategies_len(vault) == count


def strategies_len(vault):
    count = 0
    for i in range(0, 20):
        if vault.withdrawalQueue(i) == ZERO_ADDRESS:
            break

        count += 1

    return count


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
