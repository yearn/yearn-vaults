# @version 0.2.12
governance: public(address)
pendingGovernance: public(address)

event NewGovernance:
    governance: address

event NewPendingGovernance:
    governance: address

event StrategyRegistered:
    key: String[73]
    strategy: address

event Cloned:
    clone: address

interface Strategy:
    def name() -> String[64]: view
    def apiVersion() -> String[8]: view
    def initialize(params: Bytes[256]): nonpayable
    def isOriginal() -> bool: nonpayable

strategyVersions: public(HashMap[String[73], address])

@external
def __init__():
    self.governance = msg.sender

@pure
@internal
def _computeKey(name: String[64], version: String[8]) -> String[73]:
    return concat(name, "@", version)


@internal
def _key(strategy: address, name: String[64]) -> String[73]:
    strategyName: String[64] = name
    if name == "":
        strategyName = Strategy(strategy).name()
        assert strategyName != ""
    apiVersion: String[8] = Strategy(strategy).apiVersion()
    key: String[73] = self._computeKey(strategyName, apiVersion)
    return key

@external
def setGovernance(governance: address):
    """
    @notice Starts the 1st phase of the governance transfer.
    @dev Throws if the caller is not current governance.
    @param governance The next governance address
    """
    assert msg.sender == self.governance  # dev: unauthorized
    log NewPendingGovernance(governance)
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

@external
def addNewRelease(strategy :address, name: String[64] = ""):
    """
    @notice add a new version of a strategy
    """
    assert msg.sender == self.governance  # dev: unauthorized
    assert Strategy(strategy).isOriginal() # dev: not original 

    key: String[73] = self._key(strategy, name)
    self.strategyVersions[key] = strategy
    log StrategyRegistered(key, strategy)

@view 
@external
def latestRelease(name: String[64], apiVersion: String[8]) -> address:
    key: String[73] = self._computeKey(name, apiVersion)
    return self.strategyVersions[key]

@external
def clone(strategy: address,  params: Bytes[256], name: String[64] = ""):
    assert Strategy(strategy).isOriginal()  # dev: not original
    key: String[73] = self._key(strategy, name)

    assert(self.strategyVersions[key] == strategy)
    newStrategy: address = create_forwarder_to(strategy)
 
    Strategy(newStrategy).initialize(params)

    log Cloned(newStrategy)
