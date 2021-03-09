import brownie
from brownie import ZERO_ADDRESS


def test_endorsed_vault_token_tracking(
    gov, guardian, rewards, registry, Vault, create_token, create_vault, rando
):
    # Create a token and vault
    token_1 = create_token()
    vault_1 = create_vault(token_1, version="1.0.0")
    assert registry.nextRelease() == 0  # Make sure no releases have been deployed

    # Token tracking state variables should start off uninitialized
    assert registry.tokensList(0) == ZERO_ADDRESS
    assert registry.tokensMap(token_1) == False
    assert registry.tokensCount() == 0

    # Endorsing a vault registers a vault token
    registry.newRelease(vault_1, {"from": gov})
    registry.endorseVault(vault_1, {"from": gov})
    assert registry.nextRelease() == 1  # Make sure the release was deployed
    assert registry.latestVault(token_1) == vault_1
    assert registry.tokensList(0) == token_1
    assert registry.tokensList(1) == ZERO_ADDRESS
    assert registry.tokensMap(token_1) == True
    assert registry.tokensCount() == 1

    # Create a new release using the same token
    vault_2 = create_vault(token_1, version="2.0.0")
    registry.newRelease(vault_2, {"from": gov})
    assert registry.latestVault(token_1) == vault_1
    assert registry.nextRelease() == 2  # Make sure the release was deployed

    # Endorsing a vault with the same token bumps the "latestVault" associated with the token
    registry.endorseVault(vault_2, {"from": gov})
    assert registry.latestVault(token_1) == vault_2
    assert registry.latestRelease() == vault_2.apiVersion() == "2.0.0"

    # Tokens can only be registered one time (no duplicates)
    assert registry.tokensList(0) == token_1
    assert registry.tokensList(1) == ZERO_ADDRESS
    assert registry.tokensCount() == 1

    # Create a new endorsed vault with a new token
    token_2 = create_token()
    registry.newVault(token_2, guardian, rewards, "", "", {"from": gov})

    # New endorsed vaults should register tokens
    assert registry.tokensList(0) == token_1
    assert registry.tokensList(1) == token_2
    assert registry.tokensList(2) == ZERO_ADDRESS
    assert registry.tokensMap(token_1) == True
    assert registry.tokensMap(token_2) == True
    assert registry.tokensCount() == 2

    # Create a new experimental vault with a new token
    token_3 = create_token()
    vault_3 = registry.newExperimentalVault(
        token_3, gov, guardian, rewards, "", "", {"from": gov}
    ).return_value

    # New experimental (unendorsed) vaults should not register tokens
    assert registry.tokensList(0) == token_1
    assert registry.tokensList(1) == token_2
    assert registry.tokensList(2) == ZERO_ADDRESS
    assert registry.tokensMap(token_1) == True
    assert registry.tokensMap(token_2) == True
    assert registry.tokensCount() == 2

    # Endorsing a vault should register a token
    registry.endorseVault(vault_3)
    assert registry.tokensList(0) == token_1
    assert registry.tokensList(1) == token_2
    assert registry.tokensList(2) == token_3
    assert registry.tokensList(3) == ZERO_ADDRESS
    assert registry.tokensMap(token_1) == True
    assert registry.tokensMap(token_2) == True
    assert registry.tokensMap(token_3) == True
    assert registry.tokensCount() == 3


def test_deployment_management(
    gov, guardian, rewards, registry, Vault, create_token, create_vault, rando
):
    token = create_token()

    # No deployments yet for token
    with brownie.reverts():
        registry.latestVault(token)

    # Creating the first deployment makes `latestVault()` work
    v1_vault = create_vault(token, version="1.0.0")
    registry.newRelease(v1_vault, {"from": gov})
    registry.endorseVault(v1_vault, {"from": gov})
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

    # You can deploy proxy Vaults, linked to a previous release
    token = create_token()
    proxy_vault = Vault.at(
        registry.newVault(
            token, guardian, rewards, "", "", 1, {"from": gov}
        ).return_value
    )
    assert proxy_vault.apiVersion() == v1_vault.apiVersion() == "1.0.0"
    assert proxy_vault.rewards() == rewards
    assert proxy_vault.guardian() == guardian
    assert registry.latestVault(token) == proxy_vault

    # Not just anyone can create a new endorsed Vault, only governance can!
    with brownie.reverts():
        registry.newVault(create_token(), guardian, rewards, "", "", {"from": rando})


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

    # Can create an experiment and endorse it targeting a previous version
    token = create_token()
    experimental_vault = Vault.at(
        registry.newExperimentalVault(
            token, gov, gov, gov, "", "", 1, {"from": rando}
        ).return_value
    )
    registry.endorseVault(experimental_vault, 1, {"from": gov})
    assert registry.latestVault(token) == experimental_vault

    # Only governance can endorse a Vault
    vault = create_vault()
    with brownie.reverts():
        registry.endorseVault(vault, {"from": rando})
