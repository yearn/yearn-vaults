import brownie


def test_bug(token, gov, Vault, guardian, rewards, TestStrategy2):
    vault = guardian.deploy(Vault, token, gov, rewards, "", "")
    # Remove mgmt fees to avoid rounding errors
    vault.setManagementFee(0, {"from": gov})

    strategy = gov.deploy(TestStrategy2, vault)
    vault.addStrategy(strategy, 1000, 2 ** 256 - 1, 0, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    vault.deposit(1000, {"from": gov})

    token.approve(gov, 2 ** 256 - 1, {"from": gov})
    token.transferFrom(
        gov, guardian, token.balanceOf(gov), {"from": gov}
    )  # Remove all tokens from gov

    assert vault.balanceOf(gov) == 1000
    assert token.balanceOf(gov) == 0
    assert token.balanceOf(vault) == 1000

    # Deposit in the strategy
    strategy.harvest({"from": gov})
    assert token.balanceOf(strategy) == 1000
    assert token.balanceOf(vault) == 0

    # Withdraw part of the strategy funds
    vault.withdraw(400, {"from": gov})
    assert token.balanceOf(gov) == 400
    assert vault.balanceOf(gov) == 600

    # This ends up being 0
    assert token.balanceOf(strategy) != 0
