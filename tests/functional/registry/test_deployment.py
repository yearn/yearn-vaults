import brownie


def test_deployment_management(
    gov, guardian, rewards, registry, Vault, create_token, create_vault
):
    token = create_token()

    # No deployments yet for token
    with brownie.reverts():
        registry.latestVault(token)

    # Creating the first deployment makes `latestVault()` work
    v1_vault = create_vault(token, version="1.0.0")
    registry.newRelease(v1_vault, {"from": gov})
    assert registry.latestVault(token) == v1_vault
    assert registry.latestRelease() == v1_vault.apiVersion() == "1.0.0"

    # Can't deploy the same vault api version twice, proxy or not
    with brownie.reverts():
        registry.newVault(token, guardian, rewards, "", "", {"from": gov})

    # New release overrides previous release
    v2_vault = create_vault(version="2.0.0")  # Uses different token
    registry.newRelease(v2_vault, {"from": gov})
    assert registry.latestVault(token) == v1_vault
    assert registry.latestRelease() == v2_vault.apiVersion() == "2.0.0"

    # You can deploy proxy Vaults, linked to the latest release
    proxy_vault = Vault.at(
        registry.newVault(token, guardian, rewards, "", "", {"from": gov}).return_value
    )
    assert proxy_vault.apiVersion() == v2_vault.apiVersion() == "2.0.0"
    assert proxy_vault.rewards() == rewards
    assert proxy_vault.guardian() == guardian
    assert registry.latestVault(token) == proxy_vault


def test_experimental_deployments(
    gov, rando, registry, Vault, create_token, create_vault
):
    v1_vault = create_vault(version="1.0.0")
    registry.newRelease(v1_vault, {"from": gov})

    # Anyone can make an experiment
    token = create_token()
    registry.newExperimentalVault(token, rando, rando, rando, "", "", {"from": rando})

    # You can make as many experiments as you want with same api version
    experimental_vault = Vault.at(
        registry.newExperimentalVault(
            token, rando, rando, rando, "", "", {"from": rando}
        ).return_value
    )

    # Experimental Vaults do not count towards deployments
    with brownie.reverts():
        registry.latestVault(token)

    # You can't endorse a vault if governance isn't set properly
    with brownie.reverts():
        registry.endorseVault(experimental_vault, {"from": gov})

    experimental_vault.setGovernance(gov, {"from": rando})
    experimental_vault.acceptGovernance({"from": gov})

    # You can only endorse a vault if it creates an new deployment
    registry.endorseVault(experimental_vault, {"from": gov})
    assert registry.latestVault(token) == experimental_vault

    # You can't endorse a vault if it would overwrite a current deployment
    experimental_vault = Vault.at(
        registry.newExperimentalVault(
            token, gov, gov, gov, "", "", {"from": rando}
        ).return_value
    )
    with brownie.reverts():
        registry.endorseVault(experimental_vault, {"from": gov})

    # You can only endorse a vault if it creates a new deployment
    v2_vault = create_vault(version="2.0.0")
    registry.newRelease(v2_vault, {"from": gov})

    experimental_vault = Vault.at(
        registry.newExperimentalVault(
            token, gov, gov, gov, "", "", {"from": rando}
        ).return_value
    )
    registry.endorseVault(experimental_vault, {"from": gov})
    assert registry.latestVault(token) == experimental_vault
