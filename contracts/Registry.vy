# @version 0.2.8

interface DetailedERC20:
    def name() -> String[52]: view
    def symbol() -> String[30]: view


interface Vault:
    def token() -> address: view
    def apiVersion() -> String[28]: view
    def governance() -> address: view
    def initialize(
        token: address,
        governance: address,
        rewards: address,
        name: String[64],
        symbol: String[32],
        guardian: address,
    ): nonpayable


# len(Vault.releases)
nextRelease: public(uint256)
releases: public(HashMap[uint256, address])

# Token.address => len(Vault.deployments)
nextDeployment: public(HashMap[address, uint256])
vaults: public(HashMap[address, HashMap[uint256, address]])

# 2-phase commit
governance: public(address)
pendingGovernance: address

tags: public(HashMap[address, String[1000000]])
banksy: public(HashMap[address, bool])  # could be anyone

event NewRelease:
    release_id: indexed(uint256)
    template: address
    api_version: String[28]

event NewVault:
    token: indexed(address)
    deployment_id: indexed(uint256)
    vault: address
    api_version: String[28]

event NewExperimentalVault:
    token: indexed(address)
    deployer: indexed(address)
    vault: address
    api_version: String[28]

event NewGovernance:
    governance: address

event VaultTagged:
    vault: address
    tag: String[1000000]

@external
def __init__():
    self.governance = msg.sender


@external
def setGovernance(governance: address):
    """
    @notice Starts the 1st phase of the governance transfer.
    @dev Throws if the caller is not current governance.
    @param governance The next governance address
    """
    assert msg.sender == self.governance  # dev: unauthorized
    self.pendingGovernance = governance


@external
def acceptGovernance():
    """
    @notice Completes the 2nd phase of the governance transfer.
    @dev
        Throws if the caller is not the pending caller.
        Emits a `NewGovernance` event.
    """
    assert msg.sender == self.pendingGovernance  # dev: unauthorized
    self.governance = msg.sender
    log NewGovernance(msg.sender)


@view
@external
def latestRelease() -> String[28]:
    """
    @notice Returns the api version of the latest release.
    @dev Throws if no releases are registered yet.
    @return The api version of the latest release.
    """
    # NOTE: Throws if there has not been a release yet
    return Vault(self.releases[self.nextRelease - 1]).apiVersion()  # dev: no release


@view
@external
def latestVault(token: address) -> address:
    """
    @notice Returns the latest deployed vault for the given token.
    @dev Throws if no deployments are endorsed yet for the given token.
    @param token The token address to find the latest deployment for.
    @return The address of the latest deployment.
    """
    # NOTE: Throws if there has not been a deployment yet for this token
    return self.vaults[token][self.nextDeployment[token] - 1]  # dev: no vault for token


@internal
def _registerRelease(vault: address):
    api_version: String[28] = Vault(vault).apiVersion()

    # Check if the release is different from the current one
    # NOTE: This doesn't check for strict semver-style linearly increasing release versions
    release_id: uint256 = self.nextRelease  # Next id in series
    if release_id > 0:
        current_version: String[28] = Vault(self.releases[release_id - 1]).apiVersion()
        assert current_version != api_version  # dev: same api version
    # else: we are adding the first release to the Registry!

    # Update latest release
    self.releases[release_id] = vault
    self.nextRelease = release_id + 1

    # Log the release for external listeners (e.g. Graph)
    log NewRelease(release_id, vault, api_version)


@internal
def _registerDeployment(token: address, vault: address):
    api_version: String[28] = Vault(vault).apiVersion()

    # Check if there is an existing deployment for this token at the particular api version
    # NOTE: This doesn't check for strict semver-style linearly increasing release versions
    deployment_id: uint256 = self.nextDeployment[token]  # Next id in series
    if deployment_id > 0:
        current_version: String[28] = Vault(self.vaults[token][deployment_id - 1]).apiVersion()
        assert current_version != api_version  # dev: same api version
    # else: we are adding a new token to the Registry

    # Update the latest deployment
    self.vaults[token][deployment_id] = vault
    self.nextDeployment[token] = deployment_id + 1

    # Log the deployment for external listeners (e.g. Graph)
    log NewVault(token, deployment_id, vault, api_version)


@external
def newRelease(vault: address):
    """
    @notice
        Add a previously deployed Vault as the template contract for the latest release,
        to be used by further "forwarder-style" delegatecall proxy contracts that can be
        deployed from the registry throw other methods (to save gas).
    @dev
        Throws if caller isn't `self.governance`.
        Throws if `vault`'s governance isn't `self.governance`.
        Throws if the api version is the same as the previous release.
        Emits a `NewVault` event.
    @param vault The vault that will be used as the template contract for the next release.
    """
    assert msg.sender == self.governance  # dev: unauthorized
    assert Vault(vault).governance() == msg.sender  # dev: not governed

    self._registerRelease(vault)
    self._registerDeployment(Vault(vault).token(), vault)  # NOTE: Should never throw


@internal
def _newProxyVault(
    token: address,
    governance: address,
    rewards: address,
    guardian: address,
    name: String[64],
    symbol: String[32],
) -> address:
    # NOTE: Underflow if no releases created yet (this is okay)
    vault: address = create_forwarder_to(self.releases[self.nextRelease - 1])  # dev: no releases

    nameOverride: String[64] = name
    if nameOverride == "":
        nameOverride = concat(DetailedERC20(token).symbol(), " yVault")

    symbolOverride: String[32] = symbol
    if symbolOverride == "":
        symbolOverride = concat("yv", DetailedERC20(token).symbol())

    # NOTE: Must initialize the Vault atomically with deploying it
    Vault(vault).initialize(token, governance, rewards, nameOverride, symbolOverride, guardian)

    return vault


@external
def newVault(
    token: address,
    guardian: address,
    rewards: address,
    name: String[64],
    symbol: String[32],
) -> address:
    """
    @notice
        Create a new vault for the given token using the latest release in the registry,
        as a simple "forwarder-style" delegatecall proxy to the latest release. Also adds
        the new vault to the list of "endorsed" vaults for that token.
    @dev
        `governance` is set in the new vault as `self.governance`, with no ability to override.
        Throws if caller isn't `self.governance`.
        Throws if no releases are registered yet.
        Throws if there already is a deployment for the given token with the latest api version.
        Emits a `NewVault` event.
    @param token The token that may be deposited into the new Vault.
    @param guardian The address authorized for guardian interactions in the new Vault.
    @param rewards The address to use for collecting rewards in the new Vault
    @param name Specify a custom Vault name. Set to empty string for default choice.
    @param symbol Specify a custom Vault symbol name. Set to empty string for default choice.
    @return The address of the newly-deployed vault
    """
    assert msg.sender == self.governance  # dev: unauthorized

    vault: address = self._newProxyVault(token, msg.sender, rewards, guardian, name, symbol)

    self._registerDeployment(token, vault)

    return vault


@external
def newExperimentalVault(
    token: address,
    governance: address,
    guardian: address,
    rewards: address,
    name: String[64],
    symbol: String[32],
) -> address:
    """
    @notice
        Create a new vault for the given token using the latest release in the registry,
        as a simple "forwarder-style" delegatecall proxy to the latest release. Does not add
        the new vault to the list of "endorsed" vaults for that token.
    @dev
        Throws if no releases are registered yet.
        Emits a `NewExperimentalVault` event.
    @param token The token that may be deposited into the new Vault.
    @param governance The address authorized for governance interactions in the new Vault.
    @param guardian The address authorized for guardian interactions in the new Vault.
    @param rewards The address to use for collecting rewards in the new Vault
    @param name Specify a custom Vault name. Set to empty string for default choice.
    @param symbol Specify a custom Vault symbol name. Set to empty string for default choice.
    @return The address of the newly-deployed vault
    """
    # NOTE: Anyone can call this method, as a convenience to Strategist' experiments
    vault: address = self._newProxyVault(token, governance, rewards, guardian, name, symbol)

    # NOTE: Not registered, so emit an "experiment" event here instead
    log NewExperimentalVault(token, msg.sender, vault, Vault(vault).apiVersion())

    return vault


@external
def endorseVault(vault: address):
    """
    @notice
        Adds an existing vault to the list of "endorsed" vaults for that token.
    @dev
        `governance` is set in the new vault as `self.governance`, with no ability to override.
        Throws if caller isn't `self.governance`.
        Throws if `vault`'s governance isn't `self.governance`.
        Throws if no releases are registered yet.
        Throws if `vault`'s api version does not match latest release.
        Throws if there already is a deployment for the vault's token with the latest api version.
        Emits a `NewVault` event.
    @param vault The vault that will be endorsed by the Registry.
    """
    assert msg.sender == self.governance  # dev: unauthorized
    assert Vault(vault).governance() == msg.sender  # dev: not governed

    # NOTE: Underflow if no releases created yet (this is okay)
    api_version: String[28] = (
        Vault(self.releases[self.nextRelease - 1]).apiVersion()  # dev: no releases
    )
    assert Vault(vault).apiVersion() == api_version  # dev: not latest release

    # Add to the end of the list of vaults for token
    self._registerDeployment(Vault(vault).token(), vault)


@external
def setBanksy(tagger: address, allowed: bool = True):
    """
    @notice Set the ability of a particular tagger to tag current vaults.
    @dev Throws if caller is not `self.governance`.
    @param tagger The address to approve or deny access to tagging.
    @param allowed Whether to approve or deny `tagger`. Defaults to approve.
    """
    assert msg.sender == self.governance  # dev: unauthorized
    self.banksy[tagger] = allowed


@external
def tagVault(vault: address, tag: String[1000000]):
    """
    @notice Tag a Vault with a message.
    @dev
        Throws if caller is not `self.governance` or an approved tagger.
        Emits a `VaultTagged` event.
    @param vault The address to tag with the given `tag` message.
    @param tag The message to tag `vault` with.
    """
    if msg.sender != self.governance:
        assert self.banksy[msg.sender]  # dev: not banksy
    # else: we are governance, we can do anything banksy can do

    self.tags[vault] = tag
    log VaultTagged(vault, tag)
