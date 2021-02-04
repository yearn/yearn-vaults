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


def test_banksy(gov, guardian, rewards, registry, create_token, create_vault, rando):

    # Not just anyone can create a new endorsed Vault, only governance can!
    with brownie.reverts():
        registry.newVault(create_token(), guardian, rewards, "", "", {"from": rando})

    vault = create_vault()

    # Not just anyone can create a new Release either
    with brownie.reverts():
        registry.newRelease(vault, {"from": rando})

    registry.newRelease(vault)
    assert registry.tags(vault) == ""

    # Not just anyone can tag a Vault either
    with brownie.reverts():
        registry.tagVault(vault, "Anything I want!", {"from": rando})

    # Not just anyone can endorse a Vault either
    with brownie.reverts():
        registry.endorseVault(vault, {"from": rando})

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
