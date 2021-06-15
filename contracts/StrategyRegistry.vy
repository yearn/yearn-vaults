# @version 0.2.12

governance: public(address)
pendingGovernance: public(address)

event NewGovernance:
    governance: address

interface Strategy:
    def name() -> String[64]: view

struct StrategyInfo:
    name: String[64]
    numReleases: uint256 
    versions: address[20]

strategiesReleases: public(HashMap[bytes32, StrategyInfo])

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

@external
def addNewRelease(strategy :address, name: String[64] = ""):
    """
    @notice add a new version of a strategy
    """
    assert msg.sender == self.pendingGovernance  # dev: unauthorized
    strategyName: String[64] = name 
    if name == "":
        strategyName = Strategy(strategy).name()
    strategyHash: bytes32 = sha256(strategyName)
    if self.strategiesReleases[strategyHash].numReleases == 0:
	    self.strategiesReleases[strategyHash] = StrategyInfo({
		    name: strategyName,
		    numReleases: 0,
		    versions: [ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS]
	    })
    numReleases: uint256 = self.strategiesReleases[strategyHash].numReleases
    self.strategiesReleases[strategyHash].numReleases = numReleases + 1
    self.strategiesReleases[strategyHash].versions[numReleases] = strategy

@external
def latestRelease(name: String[64]) -> address:
     strategyHash: bytes32 = sha256(name)
     
     return self.strategiesReleases[strategyHash].versions[self.strategiesReleases[strategyHash].numReleases - 1]