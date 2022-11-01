import pytest
import brownie


def test_set_goverance(gov, rando, base_fee_oracle):
    with brownie.reverts():
        base_fee_oracle.setPendingGovernance(rando, {"from": rando})
    base_fee_oracle.setPendingGovernance(rando, {"from": gov})
    with brownie.reverts():
        base_fee_oracle.acceptGovernance({"from": gov})
    base_fee_oracle.acceptGovernance({"from": rando})
    with brownie.reverts():
        base_fee_oracle.setPendingGovernance(rando, {"from": gov})
    assert base_fee_oracle.governance() == rando.address


def test_set_provider(gov, rando, base_fee_oracle):
    with brownie.reverts():
        base_fee_oracle.setBaseFeeProvider(rando, {"from": rando})
    base_fee_oracle.setBaseFeeProvider(rando, {"from": gov})


def test_set_and_revoke_authorized(gov, rando, base_fee_oracle):
    with brownie.reverts():
        base_fee_oracle.setAuthorized(rando, True, {"from": rando})
    base_fee_oracle.setAuthorized(rando, True, {"from": gov})

    base_fee_oracle.setMaxAcceptableBaseFee(100, {"from": rando})
    base_fee_oracle.setMaxAcceptableBaseFee(1000, {"from": gov})

    # now revoke their access, bad rando!
    base_fee_oracle.setAuthorized(rando, False, {"from": gov})
    with brownie.reverts():
        base_fee_oracle.setMaxAcceptableBaseFee(100, {"from": rando})


def test_set_manual_and_function(gov, rando, base_fee_oracle):
    # should be true for now
    assert base_fee_oracle.isCurrentBaseFeeAcceptable({"from": gov})

    # manually set to false
    base_fee_oracle.setManualBaseFeeBool(False, {"from": gov})
    assert not base_fee_oracle.isCurrentBaseFeeAcceptable({"from": gov})

    # should be true again
    base_fee_oracle.setManualBaseFeeBool(True, {"from": gov})
    assert base_fee_oracle.isCurrentBaseFeeAcceptable({"from": gov})

    # rando can't set it
    with brownie.reverts():
        base_fee_oracle.setManualBaseFeeBool(False, {"from": rando})
