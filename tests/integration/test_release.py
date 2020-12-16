from semantic_version import Version

from brownie.test import strategy

from brownie import Vault


class ReleaseTest:

    st_bool = strategy("bool")

    def __init__(self, gov, registry, create_token, create_vault):
        self.gov = gov
        self.registry = registry
        self.create_token = lambda s: create_token()

        def create_vault_adaptor(self, *args, **kwargs):
            return create_vault(*args, **kwargs)

        self.create_vault = create_vault_adaptor

    def setup(self):
        self.latest_version = Version("1.0.0")
        token = self.create_token()
        vault = self.create_vault(token, version=str(self.latest_version))
        self.vaults = {token: [vault]}
        self.registry.newRelease(vault, {"from": self.gov})
        self.experiments = {}

    def rule_new_release(self, new_token="st_bool"):
        if new_token or len(self.vaults.keys()) == 0:
            token = self.create_token()
        else:
            token = list(self.vaults.keys())[-1]

        self.latest_version = self.latest_version.next_patch()

        vault = self.create_vault(token, version=str(self.latest_version))
        print(f"Registry.newRelease({token}, {self.latest_version})")
        self.registry.newRelease(vault, {"from": self.gov})

        if token in self.vaults:
            self.vaults[token].append(vault)
        else:
            self.vaults[token] = [vault]

    def rule_new_deployment(self, new_token="st_bool"):
        tokens_with_stale_deployments = [
            token
            for token, deployments in self.vaults.items()
            if Version(deployments[-1].apiVersion()) < self.latest_version
        ]
        if new_token or len(tokens_with_stale_deployments) == 0:
            token = self.create_token()
        else:
            token = tokens_with_stale_deployments[-1]

        print(f"Registry.newVault({token}, {self.latest_version})")
        vault = Vault.at(
            self.registry.newVault(token, self.gov, self.gov, "", "").return_value
        )

        if token in self.vaults:
            self.vaults[token].append(vault)
        else:
            self.vaults[token] = [vault]

    def rule_new_experiment(self):
        token = self.create_token()
        print(f"Registry.newExperimentalVault({token}, {self.latest_version})")

        vault = Vault.at(
            self.registry.newExperimentalVault(
                token, self.gov, self.gov, self.gov, "", ""
            ).return_value
        )

        self.experiments[token] = [vault]

    def rule_endorse_experiment(self):
        experiments_with_latest_api = [
            (token, deployments[-1])
            for token, deployments in self.experiments.items()
            if (
                Version(deployments[-1].apiVersion()) == self.latest_version
                and (
                    token not in self.vaults
                    or Version(self.vaults[token][-1].apiVersion())
                    < Version(deployments[-1].apiVersion())
                )
            )
        ]
        if len(experiments_with_latest_api) > 0:
            token, vault = experiments_with_latest_api[-1]
            print(f"Registry.endorseVault({token}, {self.latest_version})")
            self.registry.endorseVault(vault, {"from": self.gov})

            if token in self.vaults:
                self.vaults[token].append(vault)
            else:
                self.vaults[token] = [vault]

    def invariant(self):
        for token, deployments in self.vaults.items():
            # Check that token matches up
            assert deployments[0].token() == token
            # Strictly linearly increasing versions
            last_version = Version(deployments[0].apiVersion())
            assert last_version <= self.latest_version

            for vault in deployments[1:]:
                # Check that token matches up
                assert vault.token() == token
                # Strictly linearly increasing versions
                assert last_version < Version(vault.apiVersion()) <= self.latest_version


def test_releases(gov, registry, create_token, create_vault, state_machine):
    state_machine(ReleaseTest, gov, registry, create_token, create_vault)
