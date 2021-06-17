# @version 0.2.12
governance: public(address)
pendingGovernance: public(address)

event NewGovernance:
    governance: address

event NewPendingGovernance:
    governance: address

event StrategyRegistered:
    strategy: address
    name: String[64]
    apiVersion: String[8]

event Cloned:
    clone: address

interface Strategy:
    def name() -> String[64]: view
    def apiVersion() -> String[8]: view
    def initialize(params: Bytes[128]): nonpayable
    def isOriginal() -> bool: nonpayable

strategyVersions: public(HashMap[String[73], address])
SEPARATOR: constant(String[1]) = "@"

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
    log NewPendingGovernance(msg.sender)
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
    strategyName: String[64] = name 
    if name == "":
        strategyName = Strategy(strategy).name()
        assert strategyName != ""
    apiVersion: String[8] = Strategy(strategy).apiVersion()
    key: String[73] = concat(strategyName, SEPARATOR, apiVersion)
    self.strategyVersions[key] = strategy
    log StrategyRegistered(strategy, strategyName, apiVersion)
 
@external
def latestRelease(name: String[64], apiVersion: String[8]) -> address:
    key: String[73] = concat(name, SEPARATOR, apiVersion)
    return self.strategyVersions[key]

@external
def clone(strategy: address, params: Bytes[128]):
    assert Strategy(strategy).isOriginal()  # dev: not original

    newStrategy: address = create_forwarder_to(strategy)
 
    Strategy(newStrategy).initialize(params)

    log Cloned(newStrategy)
