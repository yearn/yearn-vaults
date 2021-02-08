import brownie


def test_config(gov, token, vault, registry, ytoken):
    assert ytoken.token() == token

    # No vault added to the registry yet, so these methods should fail
    assert registry.nextDeployment(token) == 0

    with brownie.reverts():
        assert ytoken.name()

    with brownie.reverts():
        assert ytoken.symbol()

    with brownie.reverts():
        assert ytoken.decimals()

    with brownie.reverts():
        ytoken.bestVault()

    # This won't revert though, there's no Vaults yet
    assert ytoken.allVaults() == []

    # Now they work when we have a Vault
    registry.newRelease(vault, {"from": gov})
    assert ytoken.bestVault() == vault
    assert ytoken.name() == vault.name()
    assert ytoken.symbol() == vault.symbol()
    assert ytoken.decimals() == vault.decimals()
    assert ytoken.allVaults() == [vault]


def test_deposit(token, registry, vault, ytoken, gov, rando):
    registry.newRelease(vault, {"from": gov})
    token.transfer(rando, 10000, {"from": gov})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 0

    # NOTE: Must approve ytoken to deposit
    token.approve(ytoken, 10000, {"from": rando})
    ytoken.deposit(10000, {"from": rando})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 10000


def test_transfer(token, registry, vault, ytoken, gov, rando, affiliate):
    registry.newRelease(vault, {"from": gov})
    token.transfer(rando, 10000, {"from": gov})
    token.approve(ytoken, 10000, {"from": rando})
    ytoken.deposit(10000, {"from": rando})

    # NOTE: Must approve ytoken to withdraw and send
    vault.approve(ytoken, 10000, {"from": rando})
    # NOTE: Just using `affiliate` as a random address
    ytoken.transfer(affiliate, 10000, {"from": rando})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 0
    assert token.balanceOf(rando) == 0
    assert token.balanceOf(affiliate) == 10000


def test_withdraw(token, registry, vault, ytoken, gov, rando):
    registry.newRelease(vault, {"from": gov})
    token.transfer(rando, 10000, {"from": gov})
    token.approve(ytoken, 10000, {"from": rando})
    ytoken.deposit(10000, {"from": rando})

    # NOTE: Must approve ytoken to withdraw
    vault.approve(ytoken, 10000, {"from": rando})
    ytoken.withdraw(10000, {"from": rando})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 0
    assert token.balanceOf(rando) == 10000
