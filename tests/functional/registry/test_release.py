import brownie


def test_release_management(gov, registry, create_vault):
    # No releases yet
    with brownie.reverts():
        registry.latestRelease()

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
