import brownie
from brownie import ZERO_ADDRESS


def test_deployment_management(
    gov,
    guardian,
    rewards,
    management,
    registry,
    Vault,
    create_token,
    create_vault,
    rando,
):
    v1_token = create_token()
    # No deployments yet for token
    with brownie.reverts():
        registry.latestVault(v1_token)

    # Token tracking state variables should start off uninitialized
    assert registry.tokens(0) == ZERO_ADDRESS
    assert not registry.isRegistered(v1_token)
    assert registry.numTokens() == 0

    # New release does not add new token
    v1_vault = create_vault(v1_token, version="1.0.0")
    registry.newRelease(v1_vault, {"from": gov})
    assert registry.tokens(0) == ZERO_ADDRESS
    assert not registry.isRegistered(v1_token)
    assert registry.numTokens() == 0

    # Creating the first deployment makes `latestVault()` work
    registry.endorseVault(v1_vault, {"from": gov})
    assert registry.latestVault(v1_token) == v1_vault
    assert registry.latestRelease() == v1_vault.apiVersion() == "1.0.0"

    # Endorsing a vault with a new token registers a new token
    assert registry.tokens(0) == v1_token
    assert registry.isRegistered(v1_token)
    assert registry.numTokens() == 1

    # Can't deploy the same vault api version twice, proxy or not
    with brownie.reverts():
        registry.newVault(v1_token, guardian, rewards, "", "", {"from": gov})

    # New release overrides previous release
    v2_vault = create_vault(version="2.0.0")  # Uses different token
    registry.newRelease(v2_vault, {"from": gov})
    assert registry.latestVault(v1_token) == v1_vault
    assert registry.latestRelease() == v2_vault.apiVersion() == "2.0.0"

    # You can deploy proxy Vaults, linked to the latest release
    assert registry.numTokens() == 1
    proxy_vault = Vault.at(
        registry.newVault(
            v1_token, guardian, rewards, "", "", {"from": gov}
        ).return_value
    )
    assert proxy_vault.apiVersion() == v2_vault.apiVersion() == "2.0.0"
    assert proxy_vault.rewards() == rewards
    assert proxy_vault.guardian() == guardian
    assert registry.latestVault(v1_token) == proxy_vault

    # Tokens can only be registered one time (no duplicates)
    assert registry.numTokens() == 1

    # You can deploy proxy Vaults, linked to a previous release
    v2_token = create_token()
    proxy_vault = Vault.at(
        registry.newVault(
            v2_token, guardian, rewards, "", "", 1, {"from": gov}
        ).return_value
    )
    assert proxy_vault.apiVersion() == v1_vault.apiVersion() == "1.0.0"
    assert proxy_vault.rewards() == rewards
    assert proxy_vault.guardian() == guardian
    assert registry.latestVault(v2_token) == proxy_vault

    # Adding a new endorsed vault with `newVault()` registers a new token
    assert registry.tokens(0) == v1_token
    assert registry.tokens(1) == v2_token
    assert registry.isRegistered(v1_token)
    assert registry.isRegistered(v2_token)
    assert registry.numTokens() == 2

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

    # New experimental (unendorsed) vaults should not register tokens
    assert registry.tokens(0) == ZERO_ADDRESS
    assert not registry.isRegistered(token)
    assert registry.numTokens() == 0

    # You can only endorse a vault if it creates an new deployment
    registry.endorseVault(experimental_vault, {"from": gov})
    assert registry.latestVault(token) == experimental_vault

    # Endorsing experimental vaults should register a token
    assert registry.tokens(0) == token
    assert registry.isRegistered(token)
    assert registry.numTokens() == 1

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
