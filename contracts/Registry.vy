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
    assert msg.sender == self.governance  # dev: unauthorized
    self.pendingGovernance = governance


@external
def acceptGovernance():
    assert msg.sender == self.pendingGovernance  # dev: unauthorized
    self.governance = msg.sender
    log NewGovernance(msg.sender)


@view
@external
def latestRelease() -> String[28]:
    # NOTE: Throws if there has not been a release yet
    return Vault(self.releases[self.nextRelease - 1]).apiVersion()  # dev: no release


@view
@external
def latestVault(token: address) -> address:
    # NOTE: Throws if there has not been a deployment yet for this token
    return self.vaults[token][self.nextDeployment[token] - 1]  # dev: no vault for token


@internal
def _endorseVault(token: address, vault: address):
    next_version: String[28] = Vault(vault).apiVersion()
    deployment_id: uint256 = self.nextDeployment[token]  # Next id in series

    # Check if there is an existing deployed vault for this token, and that we are not overwriting
    # NOTE: This doesn't check for strict semver-style linearly increasing release versions
    if deployment_id > 0:
        current_version: String[28] = Vault(self.vaults[token][deployment_id - 1]).apiVersion()
        assert next_version != current_version  # dev: cannot override current version
    # else: we are adding a new asset to the ecosystem!
    #       (typically after a successful "experimental" vault)

    self.vaults[token][deployment_id] = vault
    self.nextDeployment[token] = deployment_id + 1

    log NewVault(token, deployment_id, vault, next_version)


@external
def newRelease(vault: address):
    """
    @notice
        Add a previously deployed Vault as a vault for a particular release
    @dev
        The Vault must be a valid Vault, and should be the next in the release series, meaning
        semver is being followed. The code does not check for that, only that the release is not
        the same as the previous one.
    @param vault The deployed Vault to use as the cornerstone template for the given release.
    """
    assert msg.sender == self.governance  # dev: unauthorized

    release_id: uint256 = self.nextRelease  # Next id in series
    api_version: String[28] = Vault(vault).apiVersion()
    if release_id > 0:
        next_version: String[28] = Vault(self.releases[release_id - 1]).apiVersion()
        assert next_version != api_version  # dev: same version

    self.releases[release_id] = vault
    self.nextRelease = release_id + 1

    log NewRelease(release_id, vault, api_version)

    # Also register the release as a new Vault
    self._endorseVault(Vault(vault).token(), vault)


@internal
def _newVault(
    token: address,
    template: address,
    governance: address,
    rewards: address,
    guardian: address,
    name: String[64],
    symbol: String[32],
) -> address:

    # NOTE: Underflow if no releases created yet (this is okay)
    vault: address = create_forwarder_to(template)

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
        Add a new deployed vault for the given token as a simple "forwarder-style" proxy to the
        latest version being managed by this registry
    @dev
        If `nameOverride` is not specified, the name will be 'yearn' combined with the name of
        `token`.

        If `symbolOverride` is not specified, the symbol will be 'yv' combined with the symbol
        of `token`.
    @param token The token that may be deposited into this Vault.
    @param guardian The address authorized for guardian interactions.
    @param rewards The address to use for collecting rewards.
    @param name Specify a custom Vault name. Set to empty string for default choice.
    @param symbol Specify a custom Vault symbol name. Set to empty string for default choice.
    @return The address of the newly-deployed vault
    """
    assert msg.sender == self.governance  # dev: unauthorized

    # NOTE: Underflow if no releases created yet (this is okay)
    release_template: address = self.releases[self.nextRelease - 1]  # dev: no releases
    vault: address = self._newVault(token, release_template, msg.sender, msg.sender, guardian, name, symbol)

    self._endorseVault(token, vault)

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
    # NOTE: Anyone can call this method, as a convenience to Strategist' experiments
    # NOTE: Underflow if no releases created yet (this is okay)
    release_template: address = self.releases[self.nextRelease - 1]  # dev: no releases
    vault: address = self._newVault(token, release_template, governance, governance, guardian, name, symbol)
    # NOTE: Must initialize the Vault atomically with deploying it
    Vault(vault).initialize(token, governance, rewards, name, symbol, guardian)

    # NOTE: Don't add to list of endorsed vaults (hence no event there, so we emit here)
    log NewExperimentalVault(token, vault, Vault(release_template).apiVersion())

    return vault


@external
def endorseVault(vault: address):
    assert msg.sender == self.governance  # dev: unauthorized
    # NOTE: Underflow if no releases created yet (this is okay)
    release_template: address = self.releases[self.nextRelease - 1]  # dev: no releases
    latest_version: String[28] = Vault(release_template).apiVersion()
    assert Vault(vault).apiVersion() == latest_version  # dev: not latest release

    assert Vault(vault).governance() == msg.sender  # dev: unauthorized

    token: address = Vault(vault).token()

    # Add to the end of the list of vaults for token
    self._endorseVault(token, vault)


@external
def setBanksy(tagger: address, allowed: bool = True):
    assert msg.sender == self.governance  # dev: unauthorized
    self.banksy[tagger] = allowed


@external
def tagVault(vault: address, tag: String[1000000]):
    if msg.sender != self.governance:
        assert self.banksy[msg.sender]  # dev: not banksy
    # else: we are governance, we can do anything banksy can do
    self.tags[vault] = tag
    log VaultTagged(vault, tag)
