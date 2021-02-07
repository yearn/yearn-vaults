import brownie


def test_config(gov, token, vault, registry, affiliate_token):
    assert affiliate_token.token() == token
    assert affiliate_token.name() == "Affiliate " + token.symbol()
    assert affiliate_token.symbol() == "af" + token.symbol()
    assert affiliate_token.decimals() == vault.decimals() == token.decimals()

    # No vault added to the registry yet, so these methods should fail
    assert registry.nextDeployment(token) == 0

    with brownie.reverts():
        affiliate_token.latestVault()

    # This won't revert though, there's no Vaults yet
    assert affiliate_token.allVaults() == []

    # Now they work when we have a Vault
    registry.newRelease(vault, {"from": gov})
    assert affiliate_token.latestVault() == vault
    assert affiliate_token.allVaults() == [vault]
