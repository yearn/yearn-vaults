import pytest
import brownie


def test_vault_deployment(guardian, gov, rewards, token, Vault):
    vault = guardian.deploy(Vault, token, gov, rewards)
    # Addresses
    assert vault.governance() == gov
    assert vault.guardian() == guardian
    assert vault.rewards() == rewards
    assert vault.token() == token
    # UI Stuff
    assert vault.name() == "yearn " + token.name()
    assert vault.symbol() == "y" + token.symbol()
    assert vault.decimals() == token.decimals()

    assert vault.creditAvailable() == 0
    assert vault.debtOutstanding() == 0
    assert vault.maxAvailableShares() == 0
    assert vault.totalAssets() == 0


@pytest.mark.parametrize(
    "getter,setter,val",
    [
        ("emergencyShutdown", "setEmergencyShutdown", True),
        ("guardian", "setGuardian", None),
        ("rewards", "setRewards", None),
        ("performanceFee", "setPerformanceFee", 1000),
        ("debtLimit", "setDebtLimit", 1000),
        ("guardian", "setGuardian", None),
    ],
)
def test_vault_setParams(
    guardian, gov, rewards, token, rando, getter, setter, val, Vault
):
    if not val:
        # Can't access fixtures, so use None to mean any random address
        val = rando

    vault = guardian.deploy(Vault, token, gov, rewards)

    # Only governance can set this param
    with brownie.reverts():
        getattr(vault, setter)(val, {"from": rando})

    getattr(vault, setter)(val, {"from": gov})
    assert getattr(vault, getter)() == val


def test_vault_setGovernance(guardian, gov, rewards, token, rando, Vault):
    vault = guardian.deploy(Vault, token, gov, rewards)
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
