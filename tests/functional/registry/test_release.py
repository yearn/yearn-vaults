import brownie


def test_release_management(gov, registry, create_vault, rando):
    # No releases yet
    with brownie.reverts():
        registry.latestRelease()

    # Not just anyone can create a new Release
    vault = create_vault()
    with brownie.reverts():
        registry.newRelease(vault, {"from": rando})

    # Creating the first release makes `latestRelease()` work
    v1_vault = create_vault(version="1.0.0")
    registry.newRelease(v1_vault, {"from": gov})
    assert registry.latestRelease() == v1_vault.apiVersion() == "1.0.0"

    # Can't release same vault twice (cannot have the same api version)
    with brownie.reverts():
        registry.newRelease(v1_vault, {"from": gov})

    # New release overrides previous release
    v2_vault = create_vault(version="2.0.0")
    registry.newRelease(v2_vault, {"from": gov})
    assert registry.latestRelease() == v2_vault.apiVersion() == "2.0.0"

    # Can only endorse the latest release.
    with brownie.reverts():
        registry.endorseVault(v1_vault)

    # Check that newRelease works even if vault governance is not gov
    bad_vault = create_vault(governance=rando)
    registry.newRelease(bad_vault, {"from": gov})
