from pathlib import Path
import yaml

import pytest
import brownie


PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent.parent.parent / "ethpm-config.yaml").read_text()
)["version"]


def test_vault_deployment(guardian, gov, rewards, token, Vault):
    # Deploy the Vault without any name/symbol overrides
    vault = guardian.deploy(Vault, token, gov, rewards, "", "")
    # Addresses
    assert vault.governance() == gov
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


def test_vault_name_symbol_override(guardian, gov, rewards, token, Vault):
    # Deploy the Vault with name/symbol overrides
    vault = guardian.deploy(Vault, token, gov, rewards, "crvY yVault", "yvcrvY")
    # Assert that the overrides worked
    assert vault.name() == "crvY yVault"
    assert vault.symbol() == "yvcrvY"


@pytest.mark.parametrize(
    "getter,setter,val",
    [
        ("name", "setName", "NewName yVault"),
        ("symbol", "setSymbol", "yvNEW"),
        ("emergencyShutdown", "setEmergencyShutdown", True),
        ("guardian", "setGuardian", None),
        ("rewards", "setRewards", None),
        ("performanceFee", "setPerformanceFee", 1000),
        ("managementFee", "setManagementFee", 1000),
        ("depositLimit", "setDepositLimit", 1000),
    ],
)
def test_vault_setParams(gov, vault, rando, getter, setter, val):
    if not val:
        # Can't access fixtures, so use None to mean any random address
        val = rando

    # Only governance can set this param
    with brownie.reverts():
        getattr(vault, setter)(val, {"from": rando})

    getattr(vault, setter)(val, {"from": gov})
    assert getattr(vault, getter)() == val


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
