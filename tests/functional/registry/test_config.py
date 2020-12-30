import pytest
import brownie


def test_registry_deployment(gov, registry):
    assert registry.governance() == gov
    assert registry.nextRelease() == 0


def test_registry_setGovernance(gov, registry, rando):
    newGov = rando
    # No one can set governance but governance
    with brownie.reverts():
        registry.setGovernance(newGov, {"from": newGov})
    # Governance doesn't change until it's accepted
    registry.setGovernance(newGov, {"from": gov})
    assert registry.governance() == gov
    # Only new governance can accept a change of governance
    with brownie.reverts():
        registry.acceptGovernance({"from": gov})
    # Governance doesn't change until it's accepted
    registry.acceptGovernance({"from": newGov})
    assert registry.governance() == newGov
    # No one can set governance but governance
    with brownie.reverts():
        registry.setGovernance(newGov, {"from": gov})
    # Only new governance can accept a change of governance
    with brownie.reverts():
        registry.acceptGovernance({"from": gov})


def test_banksy(gov, registry, create_vault, rando):
    vault = create_vault()
    registry.newRelease(vault)
    assert registry.tags(vault) == ""

    # Not just anyone can tag a Vault, only a Banksy can!
    with brownie.reverts():
        registry.tagVault(vault, "Anything I want!", {"from": rando})

    # Not just anyone can become a banksy either
    with brownie.reverts():
        registry.setBanksy(rando, {"from": rando})

    assert not registry.banksy(rando)
    registry.setBanksy(rando, {"from": gov})
    assert registry.banksy(rando)

    registry.tagVault(vault, "Anything I want!", {"from": rando})
    assert registry.tags(vault) == "Anything I want!"

    registry.setBanksy(rando, False, {"from": gov})
    with brownie.reverts():
        registry.tagVault(vault, "", {"from": rando})

    assert not registry.banksy(gov)
    registry.tagVault(vault, "", {"from": gov})
