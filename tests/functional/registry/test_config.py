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
