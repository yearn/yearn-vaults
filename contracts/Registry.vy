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
def _addVault(token: address, vault: address):
    deployment_id: uint256 = self.nextDeployment[token]  # Next id in series
    self.vaults[token][deployment_id] = vault
    self.nextDeployment[token] = deployment_id + 1

    log NewVault(token, deployment_id, vault, Vault(vault).apiVersion())


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
        assert Vault(self.releases[release_id - 1]).apiVersion() != api_version  # dev: same version

    self.releases[release_id] = vault
    self.nextRelease = release_id + 1

    log NewRelease(release_id, vault, api_version)

    # Also register the release as a new Vault
    self._addVault(Vault(vault).token(), vault)


@external
def newVault(
    token: address,
    guardian: address,
    nameOverride: String[64] = "",
    symbolOverride: String[32] = "",
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
    @param nameOverride Specify a custom Vault name. Leave empty for default choice.
    @param symbolOverride Specify a custom Vault symbol name. Leave empty for default choice.
    @return The address of the newly-deployed vault
    """
    assert msg.sender == self.governance  # dev: unauthorized

    # NOTE: Underflow if no releases created yet (this is okay)
    vault: address = create_forwarder_to(self.releases[self.nextRelease - 1])

    name: String[64] = nameOverride
    if name == "":
        name = concat("Yearn ", DetailedERC20(token).name(), " Vault")

    symbol: String[32] = symbolOverride
    if symbol == "":
        symbol = concat("yv", DetailedERC20(token).symbol())

    # NOTE: Must initialize the Vault atomically with deploying it
    Vault(vault).initialize(token, msg.sender, name, symbol, guardian)

    self._addVault(token, vault)

    return vault


@external
def newExperimentalVault(
    token: address,
    governance: address = msg.sender,
    guardian: address = msg.sender,
    nameOverride: String[64] = "",
    symbolOverride: String[32] = "",
) -> address:
    # NOTE: Anyone can call this method, as a convenience to Strategist' experiments
    # NOTE: Underflow if no releases created yet (this is okay)
    release_template: address = self.releases[self.nextRelease - 1]
    vault: address = create_forwarder_to(release_template)

    name: String[64] = nameOverride
    if name == "":
        name = concat("Yearn ", DetailedERC20(token).name(), " Vault")

    symbol: String[32] = symbolOverride
    if symbol == "":
        symbol = concat("yv", DetailedERC20(token).symbol())

    # NOTE: Must initialize the Vault atomically with deploying it
    Vault(vault).initialize(token, governance, name, symbol, guardian)

    log NewExperimentalVault(token, vault, Vault(release_template).apiVersion())

    return vault


@external
def endorseVault(vault: address):
    assert msg.sender == self.governance  # dev: unauthorized
    # NOTE: Underflow if no releases created yet (this is okay)
    latest_version: String[28] = Vault(self.releases[self.nextRelease - 1]).apiVersion()
    assert Vault(vault).apiVersion() == latest_version  # dev: not latest release

    assert Vault(vault).governance() == msg.sender  # dev: unauthorized

    # Check if there is an existing deployed vault for this token, and that we are not overwriting
    # NOTE: This doesn't check for strict semver-style linearly increasing release versions
    token: address = Vault(vault).token()
    nextDeployment: uint256 = self.nextDeployment[token]
    if nextDeployment > 0:
        current_version: String[28] = Vault(self.vaults[token][nextDeployment - 1]).apiVersion()
        assert current_version != latest_version  # dev: cannot override current version
    # else: we are adding a new asset to the ecosystem!
    #       (typically after a successful "experimental" vault)

    # Add to the end of the list of vaults for token
    self._addVault(token, vault)
