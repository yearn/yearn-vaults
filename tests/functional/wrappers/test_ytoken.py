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
