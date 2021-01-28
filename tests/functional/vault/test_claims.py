import pytest
import brownie

@pytest.fixture
def vault(gov, token, claimToken, Vault):
    # NOTE: Overriding the one in conftest because it has values already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, claimToken, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    yield vault


def test_deposit_transfer(gov, vault, token, claimToken, rando):
    balance = token.balanceOf(gov)
    claimTokenBalance = claimToken.balanceOf(gov)
    token.approve(vault, balance, {"from": gov})
    vault.deposit(1000, {"from": gov})

    assert token.balanceOf(vault) == 1000
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    # Deposit 10000 claim tokens
    # The vault just assumes only strategies would do this
    claimToken.transfer(vault, 10000, {"from": gov})
    vault.update({"from": gov})
    claimBalance = vault.claimBalance()

    assert claimBalance == 10000
    
    vault.claim({"from": gov})

    # All tokens should have gone to the sole depositor
    assert claimToken.balanceOf(gov) == claimTokenBalance

    # Now deposit 10000 -> Send half of vault tokens to rando -> deposit 10000 -> both claim
    # Gov should get 15000 and rando should get 5000
    claimToken.transfer(vault, 10000, {"from": gov})
    vaultBalance = vault.balanceOf(gov)

    vault.transfer(rando, 500, {"from": gov})
    claimToken.transfer(vault, 10000, {"from": gov})

    vault.claim({"from": gov})
    vault.claim({"from": rando})

    assert claimToken.balanceOf(rando) == 5000
    assert claimToken.balanceOf(gov) == claimTokenBalance - 5000

# Here we want to test that you cannot claim more than your tokens share by sending to a new account
def test_multiple_account_claim(gov, vault, token, claimToken, rando, rando2):
    token.transfer(rando, 10000, {"from": gov})

    claimTokenBalance = claimToken.balanceOf(gov)
    token.approve(vault, 10000, {"from": gov})
    vault.deposit(10000, {"from": gov})

    # Deposit 10000 claim tokens
    # The vault just assumes only strategies would do this
    claimToken.transfer(vault, 10000, {"from": gov})
    vault.update({"from": gov})
    claimBalance = vault.claimBalance()

    assert claimBalance == 10000

    # Now we want to deposit 10000 again. Gov will be due 20000
    claimToken.transfer(vault, 10000, {"from": gov})
    vault.updateFor(gov, {"from": gov})
    claimBalance = vault.claimBalance()

    # All tokens should have gone to the sole depositor
    assert claimBalance == 20000
    assert vault.claimable(gov) == 20000

    # Now rando deposits
    token.approve(vault, 10000, {"from": rando})
    vault.deposit(10000, {"from": rando})

    # Now we want to deposit 10000 again. Gov will be due 25000 and rando 5000
    claimToken.transfer(vault, 10000, {"from": gov})
    vault.updateFor(gov, {"from": gov})
    vault.updateFor(rando, {"from": gov})
    claimBalance = vault.claimBalance()

    # All tokens should have gone to the sole depositor
    assert claimBalance == 30000
    assert vault.claimable(gov) == 25000
    assert vault.claimable(rando) == 5000

    # Now rando claims
    vault.claim({"from": rando})

    assert vault.claimable(gov) == 25000
    assert vault.claimable(rando) == 0

    # Transfer tokens to rando2
    vault.transfer(rando2, 10000, {"from": rando})

    # There are 25000 tokens to be claimed but rando2 gets none
    vault.claim({"from": rando2})
    vault.claim({"from": gov})

    assert claimToken.balanceOf(rando) == 5000
    assert claimToken.balanceOf(rando2) == 0
    assert claimToken.balanceOf(gov) == claimTokenBalance - 5000

def test_deposit_withdraw(gov, vault, token, claimToken, rando):
    balance = token.balanceOf(gov)
    claimTokenBalance = claimToken.balanceOf(gov)
    token.approve(vault, balance, {"from": gov})
    vault.deposit(1000, {"from": gov})

    # Deposit 10000 claim tokens
    # The vault just assumes only strategies would do this
    claimToken.transfer(vault, 10000, {"from": gov})
    vault.update({"from": gov})
    claimBalance = vault.claimBalance()

    assert claimBalance == 10000

    # Now gov withdraws. This should lock in we only get 10000 tokens
    vault.withdraw({"from": gov})

    claimToken.transfer(vault, 20000, {"from": gov})
    vault.claim({"from": gov})
    claimBalance = vault.claimBalance()

    assert claimBalance == 20000
   
    assert claimToken.balanceOf(vault) == 20000
    assert claimToken.balanceOf(gov) == claimTokenBalance - 20000