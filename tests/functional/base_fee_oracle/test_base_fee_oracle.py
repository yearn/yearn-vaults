import pytest
import brownie


@pytest.fixture
def base_fee_oracle(gov, BaseFeeOracle):
    yield gov.deploy(BaseFeeOracle)


def test_set_goverance(gov, rando, base_fee_oracle):
    with brownie.reverts():
        base_fee_oracle.setGovernance(rando, {"from": rando})
    base_fee_oracle.setGovernance(rando, {"from": gov})


def test_set_and_revoke_authorized(gov, rando, base_fee_oracle):
    with brownie.reverts():
        base_fee_oracle.setAuthorized(rando, {"from": rando})
    base_fee_oracle.setAuthorized(rando, {"from": gov})
    base_fee_oracle.setMaxAcceptableBaseFee(100, {"from": rando})

    # now revoke their access, bad rando!
    base_fee_oracle.revokeAuthorized(rando, {"from": gov})
    with brownie.reverts():
        base_fee_oracle.setMaxAcceptableBaseFee(100, {"from": rando})


def test_use_testing(gov, rando, base_fee_oracle):
    # sadly, can't get to 100% coverage here due to needing to connect
    # to non-development network to hit all branches, but 'else' branch
    # of isCurrentBaseFeeAcceptable has been well-tested on mainnet.
    with brownie.reverts():
        base_fee_oracle.isCurrentBaseFeeAcceptable({"from": gov})

    base_fee_oracle.setUseTesting(True, {"from": gov})
    with brownie.reverts():
        base_fee_oracle.setUseTesting(False, {"from": rando})
    base_fee_oracle.isCurrentBaseFeeAcceptable({"from": gov})
    base_fee_oracle.setUseTesting(False, {"from": gov})
    with brownie.reverts():
        base_fee_oracle.isCurrentBaseFeeAcceptable({"from": gov})
