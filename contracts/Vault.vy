# @version 0.2.8
"""
@title Yearn Token Vault
@license GNU AGPLv3
@author yearn.finance
@notice
    Yearn Token Vault. Holds an underlying token, and allows users to interact
    with the Yearn ecosystem through Strategies connected to the Vault.
    Vaults are not limited to a single Strategy, they can have as many Strategies
    as can be designed (however the withdrawal queue is capped at 20.)

    Deposited funds are moved into the most impactful strategy that has not
    already reached its limit for assets under management, regardless of which
    Strategy a user's funds end up in, they receive their portion of yields
    generated across all Strategies.

    When a user withdraws, if there are no funds sitting undeployed in the
    Vault, the Vault withdraws funds from Strategies in the order of least
    impact. (Funds are taken from the Strategy that will disturb everyone's
    gains the least, then the next least, etc.) In order to achieve this, the
    withdrawal queue's order must be properly set and managed by the community
    (through governance).

    Vault Strategies are parameterized to pursue the highest risk-adjusted yield.

    There is an "Emergency Shutdown" mode. When the Vault is put into emergency
    shutdown, assets will be recalled from the Strategies as quickly as is
    practical (given on-chain conditions), minimizing loss. Deposits are
    halted, new Strategies may not be added, and each Strategy exits with the
    minimum possible damage to position, while opening up deposits to be
    withdrawn by users. There are no restrictions on withdrawals above what is
    expected under Normal Operation.

    For further details, please refer to the specification:
    https://github.com/iearn-finance/yearn-vaults/blob/master/SPECIFICATION.md
"""

API_VERSION: constant(String[28]) = "0.3.1"

from vyper.interfaces import ERC20

implements: ERC20


interface DetailedERC20:
    def name() -> String[42]: view
    def symbol() -> String[20]: view
    def decimals() -> uint256: view


interface Strategy:
    def want() -> address: view
    def vault() -> address: view
    def isActive() -> bool: view
    def estimatedTotalAssets() -> uint256: view
    def withdraw(_amount: uint256) -> uint256: nonpayable
    def migrate(_newStrategy: address): nonpayable


interface GuestList:
    def authorized(guest: address, amount: uint256) -> bool: view


event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256


event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256


name: public(String[64])
symbol: public(String[32])
decimals: public(uint256)

balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])
totalSupply: public(uint256)

token: public(ERC20)
governance: public(address)
management: public(address)
guardian: public(address)
pendingGovernance: address
guestList: public(GuestList)

struct StrategyParams:
    performanceFee: uint256  # Strategist's fee (basis points)
    activation: uint256  # Activation block.timestamp
    debtRatio: uint256  # Maximum borrow amount (in BPS of total assets)
    minDebtPerHarvest: uint256  # Lower limit on the increase of debt since last harvest
    maxDebtPerHarvest: uint256  # Upper limit on the increase of debt since last harvest
    lastReport: uint256  # block.timestamp of the last time a report occured
    totalDebt: uint256  # Total outstanding debt that Strategy has
    totalGain: uint256  # Total returns that Strategy has realized for Vault
    totalLoss: uint256  # Total losses that Strategy has realized for Vault


event StrategyAdded:
    strategy: indexed(address)
    debtRatio: uint256  # Maximum borrow amount (in BPS of total assets)
    minDebtPerHarvest: uint256  # Lower limit on the increase of debt since last harvest
    maxDebtPerHarvest: uint256  # Upper limit on the increase of debt since last harvest
    performanceFee: uint256  # Strategist's fee (basis points)


event StrategyReported:
    strategy: indexed(address)
    gain: uint256
    loss: uint256
    debtPaid: uint256
    totalGain: uint256
    totalLoss: uint256
    totalDebt: uint256
    debtAdded: uint256
    debtRatio: uint256


event UpdateGovernance:
    governance: address # New active governance


event UpdateManagement:
    management: address # New active manager


event UpdateGuestList:
    guestList: address # Vault guest list address


event UpdateRewards:
    rewards: address # New active rewards recipient


event UpdateDepositLimit:
    depositLimit: uint256 # New active deposit limit


event UpdatePerformanceFee:
    performanceFee: uint256 # New active performance fee


event UpdateManagementFee:
    managementFee: uint256 # New active management fee


event UpdateGuardian:
    guardian: address # Address of the active guardian


event EmergencyShutdown:
    active: bool # New emergency shutdown state (if false, normal operation enabled)


event UpdateWithdrawalQueue:
    queue: address[MAXIMUM_STRATEGIES] # New active withdrawal queue


event StrategyUpdateDebtRatio:
    strategy: indexed(address) # Address of the strategy for the debt ratio adjustment
    debtRatio: uint256 # The new debt limit for the strategy (in BPS of total assets)


event StrategyUpdateMinDebtPerHarvest:
    strategy: indexed(address) # Address of the strategy for the rate limit adjustment
    minDebtPerHarvest: uint256  # Lower limit on the increase of debt since last harvest


event StrategyUpdateMaxDebtPerHarvest:
    strategy: indexed(address) # Address of the strategy for the rate limit adjustment
    maxDebtPerHarvest: uint256  # Upper limit on the increase of debt since last harvest


event StrategyUpdatePerformanceFee:
    strategy: indexed(address) # Address of the strategy for the performance fee adjustment
    performanceFee: uint256 # The new performance fee for the strategy


event StrategyMigrated:
    oldVersion: indexed(address) # Old version of the strategy to be migrated
    newVersion: indexed(address) # New version of the strategy


event StrategyRevoked:
    strategy: indexed(address) # Address of the strategy that is revoked


event StrategyRemovedFromQueue:
    strategy: indexed(address) # Address of the strategy that is removed from the withdrawal queue


event StrategyAddedToQueue:
    strategy: indexed(address) # Address of the strategy that is added to the withdrawal queue



# NOTE: Track the total for overhead targeting purposes
strategies: public(HashMap[address, StrategyParams])
MAXIMUM_STRATEGIES: constant(uint256) = 20

# Ordering that `withdraw` uses to determine which strategies to pull funds from
# NOTE: Does *NOT* have to match the ordering of all the current strategies that
#       exist, but it is recommended that it does or else withdrawal depth is
#       limited to only those inside the queue.
# NOTE: Ordering is determined by governance, and should be balanced according
#       to risk, slippage, and/or volatility. Can also be ordered to increase the
#       withdrawal speed of a particular Strategy.
# NOTE: The first time a ZERO_ADDRESS is encountered, it stops withdrawing
withdrawalQueue: public(address[MAXIMUM_STRATEGIES])

emergencyShutdown: public(bool)

depositLimit: public(uint256)  # Limit for totalAssets the Vault can hold
debtRatio: public(uint256)  # Debt ratio for the Vault across all strategies (in BPS, <= 10k)
totalDebt: public(uint256)  # Amount of tokens that all strategies have borrowed
lastReport: public(uint256)  # block.timestamp of last report
activation: public(uint256)  # block.timestamp of contract deployment
lockedProfit: public(uint256) # how much profit is locked and cant be withdrawn

lockedProfitDegration: public(uint256) # rate per block of degration. 1e18 is 100% per block
rewards: public(address)  # Rewards contract where Governance fees are sent to
# Governance Fee for management of Vault (given to `rewards`)
managementFee: public(uint256)
# Governance Fee for performance of Vault (given to `rewards`)
performanceFee: public(uint256)
MAX_BPS: constant(uint256) = 10_000  # 100%, or 10k basis points
SECS_PER_YEAR: constant(uint256) = 31_557_600  # 365.25 days
# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_SEPARATOR: public(bytes32)
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")


@external
def initialize(
    token: address,
    governance: address,
    rewards: address,
    nameOverride: String[64],
    symbolOverride: String[32],
    guardian: address = msg.sender,
):
    """
    @notice
        Initializes the Vault, this is called only once, when the contract is
        deployed.
        The performance fee is set to 10% of yield, per Strategy.
        The management fee is set to 2%, per year.
        The initial deposit limit is set to 0 (deposits disabled); it must be
        updated after initialization.
    @dev
        If `nameOverride` is not specified, the name will be 'yearn'
        combined with the name of `token`.

        If `symbolOverride` is not specified, the symbol will be 'y'
        combined with the symbol of `token`.
    @param token The token that may be deposited into this Vault.
    @param governance The address authorized for governance interactions.
    @param rewards The address to distribute rewards to.
    @param nameOverride Specify a custom Vault name. Leave empty for default choice.
    @param symbolOverride Specify a custom Vault symbol name. Leave empty for default choice.
    @param guardian The address authorized for guardian interactions. Defaults to caller.
    """
    assert self.activation == 0  # dev: no devops199
    self.token = ERC20(token)
    if nameOverride == "":
        self.name = concat(DetailedERC20(token).symbol(), " yVault")
    else:
        self.name = nameOverride
    if symbolOverride == "":
        self.symbol = concat("yv", DetailedERC20(token).symbol())
    else:
        self.symbol = symbolOverride
    self.decimals = DetailedERC20(token).decimals()
    self.governance = governance
    log UpdateGovernance(governance)
    self.management = governance
    log UpdateManagement(governance)
    self.rewards = rewards
    log UpdateRewards(rewards)
    self.guardian = guardian
    log UpdateGuardian(guardian)
    self.performanceFee = 1000  # 10% of yield (per Strategy)
    log UpdatePerformanceFee(convert(1000, uint256))
    self.managementFee = 200  # 2% per year
    log UpdateManagementFee(convert(200, uint256))
    self.lastReport = block.timestamp
    self.activation = block.timestamp
    self.lockedProfitDegration = convert(0.000046 * 1e18, uint256) # 6 hours in blocks
    # EIP-712
    self.DOMAIN_SEPARATOR = keccak256(
        concat(
            DOMAIN_TYPE_HASH,
            keccak256(convert("Yearn Vault", Bytes[11])),
            keccak256(convert(API_VERSION, Bytes[28])),
            convert(chain.id, bytes32),
            convert(self, bytes32)
        )
    )


@pure
@external
def apiVersion() -> String[28]:
    """
    @notice
        Used to track the deployed version of this contract. In practice you
        can use this version number to compare with Yearn's GitHub and
        determine which version of the source matches this deployed contract.
    @dev
        All strategies must have an `apiVersion()` that matches the Vault's
        `API_VERSION`.
    @return API_VERSION which holds the current version of this contract.
    """
    return API_VERSION


@external
def setName(name: String[42]):
    """
    @notice
        Used to change the value of `name`.

        This may only be called by governance.
    @param name The new name to use.
    """
    assert msg.sender == self.governance
    self.name = name


@external
def setSymbol(symbol: String[20]):
    """
    @notice
        Used to change the value of `symbol`.

        This may only be called by governance.
    @param symbol The new symbol to use.
    """
    assert msg.sender == self.governance
    self.symbol = symbol


# 2-phase commit for a change in governance
@external
def setGovernance(governance: address):
    """
    @notice
        Nominate a new address to use as governance.

        The change does not go into effect immediately. This function sets a
        pending change, and the governance address is not updated until
        the proposed governance address has accepted the responsibility.

        This may only be called by the current governance address.
    @param governance The address requested to take over Vault governance.
    """
    assert msg.sender == self.governance
    self.pendingGovernance = governance


@external
def acceptGovernance():
    """
    @notice
        Once a new governance address has been proposed using setGovernance(),
        this function may be called by the proposed address to accept the
        responsibility of taking over governance for this contract.

        This may only be called by the proposed governance address.
    @dev
        setGovernance() should be called by the existing governance address,
        prior to calling this function.
    """
    assert msg.sender == self.pendingGovernance
    self.governance = msg.sender
    log UpdateGovernance(msg.sender)


@external
def setManagement(management: address):
    """
    @notice
        Changes the management address.
        Management is able to make some investment decisions adjusting parameters.

        This may only be called by governance.
    @param management The address to use for managing.
    """
    assert msg.sender == self.governance
    self.management = management
    log UpdateManagement(management)


@external
def setGuestList(guestList: address):
    """
    @notice
        Used to set or change `guestList`. A guest list is another contract
        that dictates who is allowed to participate in a Vault (and transfer
        shares).

        This may only be called by governance.
    @param guestList The address of the `GuestList` contract to use.
    """
    assert msg.sender == self.governance
    self.guestList = GuestList(guestList)
    log UpdateGuestList(guestList)


@external
def setRewards(rewards: address):
    """
    @notice
        Changes the rewards address. Any distributed rewards
        will cease flowing to the old address and begin flowing
        to this address once the change is in effect.

        This will not change any Strategy reports in progress, only
        new reports made after this change goes into effect.

        This may only be called by governance.
    @param rewards The address to use for collecting rewards.
    """
    assert msg.sender == self.governance
    self.rewards = rewards
    log UpdateRewards(rewards)

@external
def setLockedProfitDegration(degration: uint256):
    """
    @notice
        Changes the locked profit degration. 
    @param degration The rate of degration in percent per second scaled to 1e18.
    """
    assert msg.sender == self.governance
    self.lockedProfitDegration = degration

@external
def setDepositLimit(limit: uint256):
    """
    @notice
        Changes the maximum amount of tokens that can be deposited in this Vault.

        Note, this is not how much may be deposited by a single depositor,
        but the maximum amount that may be deposited across all depositors.

        This may only be called by governance.
    @param limit The new deposit limit to use.
    """
    assert msg.sender == self.governance
    self.depositLimit = limit
    log UpdateDepositLimit(limit)


@external
def setPerformanceFee(fee: uint256):
    """
    @notice
        Used to change the value of `performanceFee`.

        Should set this value below the maximum strategist performance fee.

        This may only be called by governance.
    @param fee The new performance fee to use.
    """
    assert msg.sender == self.governance
    assert fee <= MAX_BPS
    self.performanceFee = fee
    log UpdatePerformanceFee(fee)


@external
def setManagementFee(fee: uint256):
    """
    @notice
        Used to change the value of `managementFee`.

        This may only be called by governance.
    @param fee The new management fee to use.
    """
    assert msg.sender == self.governance
    assert fee <= MAX_BPS
    self.managementFee = fee
    log UpdateManagementFee(fee)


@external
def setGuardian(guardian: address):
    """
    @notice
        Used to change the address of `guardian`.

        This may only be called by governance or the existing guardian.
    @param guardian The new guardian address to use.
    """
    assert msg.sender in [self.guardian, self.governance]
    self.guardian = guardian
    log UpdateGuardian(guardian)


@external
def setEmergencyShutdown(active: bool):
    """
    @notice
        Activates or deactivates Vault mode where all Strategies go into full
        withdrawal.

        During Emergency Shutdown:
        1. No Users may deposit into the Vault (but may withdraw as usual.)
        2. Governance may not add new Strategies.
        3. Each Strategy must pay back their debt as quickly as reasonable to
            minimally affect their position.
        4. Only Governance may undo Emergency Shutdown.

        See contract level note for further details.

        This may only be called by governance or the guardian.
    @param active
        If true, the Vault goes into Emergency Shutdown. If false, the Vault
        goes back into Normal Operation.
    """
    if active:
        assert msg.sender in [self.guardian, self.governance]
    else:
        assert msg.sender == self.governance
    self.emergencyShutdown = active
    log EmergencyShutdown(active)


@external
def setWithdrawalQueue(queue: address[MAXIMUM_STRATEGIES]):
    """
    @notice
        Updates the withdrawalQueue to match the addresses and order specified
        by `queue`.

        There can be fewer strategies than the maximum, as well as fewer than
        the total number of strategies active in the vault. `withdrawalQueue`
        will be updated in a gas-efficient manner, assuming the input is well-
        ordered with 0x0 only at the end.

        This may only be called by governance or management.
    @dev
        This is order sensitive, specify the addresses in the order in which
        funds should be withdrawn (so `queue`[0] is the first Strategy withdrawn
        from, `queue`[1] is the second, etc.)

        This means that the least impactful Strategy (the Strategy that will have
        its core positions impacted the least by having funds removed) should be
        at `queue`[0], then the next least impactful at `queue`[1], and so on.
    @param queue
        The array of addresses to use as the new withdrawal queue. This is
        order sensitive.
    """
    assert msg.sender in [self.management, self.governance]
    # HACK: Temporary until Vyper adds support for Dynamic arrays
    for i in range(MAXIMUM_STRATEGIES):
        if queue[i] == ZERO_ADDRESS and self.withdrawalQueue[i] == ZERO_ADDRESS:
            break
        assert self.strategies[queue[i]].activation > 0
        self.withdrawalQueue[i] = queue[i]
    log UpdateWithdrawalQueue(queue)


@internal
def erc20_safe_transfer(token: address, receiver: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # HACK: Used to handle non-compliant tokens like USDT
    response: Bytes[32] = raw_call(
        token,
        concat(
            method_id("transfer(address,uint256)"),
            convert(receiver, bytes32),
            convert(amount, bytes32),
        ),
        max_outsize=32,
    )
    if len(response) > 0:
        assert convert(response, bool), "Transfer failed!"


@internal
def erc20_safe_transferFrom(token: address, sender: address, receiver: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # HACK: Used to handle non-compliant tokens like USDT
    response: Bytes[32] = raw_call(
        token,
        concat(
            method_id("transferFrom(address,address,uint256)"),
            convert(sender, bytes32),
            convert(receiver, bytes32),
            convert(amount, bytes32),
        ),
        max_outsize=32,
    )
    if len(response) > 0:
        assert convert(response, bool), "Transfer failed!"


@internal
def _transfer(sender: address, receiver: address, amount: uint256):
    # See note on `transfer()`.

    # Protect people from accidentally sending their shares to bad places
    assert not (receiver in [self, ZERO_ADDRESS])
    self.balanceOf[sender] -= amount
    self.balanceOf[receiver] += amount
    log Transfer(sender, receiver, amount)


@external
def transfer(receiver: address, amount: uint256) -> bool:
    """
    @notice
        Transfers shares from the caller's address to `receiver`. This function
        will always return true, unless the user is attempting to transfer
        shares to this contract's address, or to 0x0.
    @param receiver
        The address shares are being transferred to. Must not be this contract's
        address, must not be 0x0.
    @param amount The quantity of shares to transfer.
    @return
        True if transfer is sent to an address other than this contract's or
        0x0, otherwise the transaction will fail.
    """
    self._transfer(msg.sender, receiver, amount)
    return True


@external
def transferFrom(sender: address, receiver: address, amount: uint256) -> bool:
    """
    @notice
        Transfers `amount` shares from `sender` to `receiver`. This operation will
        always return true, unless the user is attempting to transfer shares
        to this contract's address, or to 0x0.

        Unless the caller has given this contract unlimited approval,
        transfering shares will decrement the caller's `allowance` by `amount`.
    @param sender The address shares are being transferred from.
    @param receiver
        The address shares are being transferred to. Must not be this contract's
        address, must not be 0x0.
    @param amount The quantity of shares to transfer.
    @return
        True if transfer is sent to an address other than this contract's or
        0x0, otherwise the transaction will fail.
    """
    # Unlimited approval (saves an SSTORE)
    if (self.allowance[sender][msg.sender] < MAX_UINT256):
        allowance: uint256 = self.allowance[sender][msg.sender] - amount
        self.allowance[sender][msg.sender] = allowance
        # NOTE: Allows log filters to have a full accounting of allowance changes
        log Approval(sender, msg.sender, allowance)
    self._transfer(sender, receiver, amount)
    return True


@external
def approve(spender: address, amount: uint256) -> bool:
    """
    @dev Approve the passed address to spend the specified amount of tokens on behalf of
         `msg.sender`. Beware that changing an allowance with this method brings the risk
         that someone may use both the old and the new allowance by unfortunate transaction
         ordering. See https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    @param spender The address which will spend the funds.
    @param amount The amount of tokens to be spent.
    """
    self.allowance[msg.sender][spender] = amount
    log Approval(msg.sender, spender, amount)
    return True


@external
def increaseAllowance(spender: address, amount: uint256) -> bool:
    """
    @dev Increase the allowance of the passed address to spend the total amount of tokens
         on behalf of msg.sender. This method mitigates the risk that someone may use both
         the old and the new allowance by unfortunate transaction ordering.
         See https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    @param spender The address which will spend the funds.
    @param amount The amount of tokens to increase the allowance by.
    """
    self.allowance[msg.sender][spender] += amount
    log Approval(msg.sender, spender, self.allowance[msg.sender][spender])
    return True


@external
def decreaseAllowance(spender: address, amount: uint256) -> bool:
    """
    @dev Decrease the allowance of the passed address to spend the total amount of tokens
         on behalf of msg.sender. This method mitigates the risk that someone may use both
         the old and the new allowance by unfortunate transaction ordering.
         See https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    @param spender The address which will spend the funds.
    @param amount The amount of tokens to decrease the allowance by.
    """
    self.allowance[msg.sender][spender] -= amount
    log Approval(msg.sender, spender, self.allowance[msg.sender][spender])
    return True


@external
def permit(owner: address, spender: address, amount: uint256, expiry: uint256, signature: Bytes[65]) -> bool:
    """
    @notice
        Approves spender by owner's signature to expend owner's tokens.
        See https://eips.ethereum.org/EIPS/eip-2612.

    @param owner The address which is a source of funds and has signed the Permit.
    @param spender The address which is allowed to spend the funds.
    @param amount The amount of tokens to be spent.
    @param expiry The timestamp after which the Permit is no longer valid.
    @param signature A valid secp256k1 signature of Permit by owner encoded as r, s, v.
    @return True, if transaction completes successfully
    """
    assert owner != ZERO_ADDRESS  # dev: invalid owner
    assert expiry == 0 or expiry >= block.timestamp  # dev: permit expired
    nonce: uint256 = self.nonces[owner]
    digest: bytes32 = keccak256(
        concat(
            b'\x19\x01',
            self.DOMAIN_SEPARATOR,
            keccak256(
                concat(
                    PERMIT_TYPE_HASH,
                    convert(owner, bytes32),
                    convert(spender, bytes32),
                    convert(amount, bytes32),
                    convert(nonce, bytes32),
                    convert(expiry, bytes32),
                )
            )
        )
    )
    # NOTE: signature is packed as r, s, v
    r: uint256 = convert(slice(signature, 0, 32), uint256)
    s: uint256 = convert(slice(signature, 32, 32), uint256)
    v: uint256 = convert(slice(signature, 64, 1), uint256)
    assert ecrecover(digest, v, r, s) == owner  # dev: invalid signature
    self.allowance[owner][spender] = amount
    self.nonces[owner] = nonce + 1
    log Approval(owner, spender, amount)
    return True


@view
@internal
def _totalAssets() -> uint256:
    # See note on `totalAssets()`.
    return self.token.balanceOf(self) + self.totalDebt


@view
@external
def totalAssets() -> uint256:
    """
    @notice
        Returns the total quantity of all assets under control of this
        Vault, whether they're loaned out to a Strategy, or currently held in
        the Vault.
    @return The total assets under control of this Vault.
    """
    return self._totalAssets()


@internal
def _issueSharesForAmount(to: address, amount: uint256) -> uint256:
    # Issues `amount` Vault shares to `to`.
    # Shares must be issued prior to taking on new collateral, or
    # calculation will be wrong. This means that only *trusted* tokens
    # (with no capability for exploitative behavior) can be used.
    shares: uint256 = 0
    # HACK: Saves 2 SLOADs (~4000 gas)
    totalSupply: uint256 = self.totalSupply
    if totalSupply > 0:
        # Mint amount of shares based on what the Vault is managing overall
        # NOTE: if sqrt(token.totalSupply()) > 1e39, this could potentially revert
        shares = amount * totalSupply / self._totalAssets()
    else:
        # No existing shares, so mint 1:1
        shares = amount

    # Mint new shares
    self.totalSupply = totalSupply + shares
    self.balanceOf[to] += shares
    log Transfer(ZERO_ADDRESS, to, shares)

    return shares


@external
@nonreentrant("withdraw")
def deposit(_amount: uint256 = MAX_UINT256, recipient: address = msg.sender) -> uint256:
    """
    @notice
        Deposits `_amount` `token`, issuing shares to `recipient`. If the
        Vault is in Emergency Shutdown, deposits will not be accepted and this
        call will fail.
    @dev
        Measuring quantity of shares to issues is based on the total
        outstanding debt that this contract has ("expected value") instead
        of the total balance sheet it has ("estimated value") has important
        security considerations, and is done intentionally. If this value were
        measured against external systems, it could be purposely manipulated by
        an attacker to withdraw more assets than they otherwise should be able
        to claim by redeeming their shares.

        On deposit, this means that shares are issued against the total amount
        that the deposited capital can be given in service of the debt that
        Strategies assume. If that number were to be lower than the "expected
        value" at some future point, depositing shares via this method could
        entitle the depositor to *less* than the deposited value once the
        "realized value" is updated from further reports by the Strategies
        to the Vaults.

        Care should be taken by integrators to account for this discrepancy,
        by using the view-only methods of this contract (both off-chain and
        on-chain) to determine if depositing into the Vault is a "good idea".
    @param _amount The quantity of tokens to deposit, defaults to all.
    @param recipient
        The address to issue the shares in this Vault to. Defaults to the
        caller's address.
    @return The issued Vault shares.
    """
    assert not self.emergencyShutdown  # Deposits are locked out

    amount: uint256 = _amount

    # If _amount not specified, transfer the full token balance,
    # up to deposit limit
    if amount == MAX_UINT256:
        amount = min(
            self.depositLimit - self._totalAssets(),
            self.token.balanceOf(msg.sender),
        )
    else:
        # Ensure deposit limit is respected
        assert self._totalAssets() + amount <= self.depositLimit

    # Ensure we are depositing something
    assert amount > 0

    # Ensure deposit is permitted by guest list
    if self.guestList.address != ZERO_ADDRESS:
        assert self.guestList.authorized(msg.sender, amount)

    # Issue new shares (needs to be done before taking deposit to be accurate)
    # Shares are issued to recipient (may be different from msg.sender)
    # See @dev note, above.
    shares: uint256 = self._issueSharesForAmount(recipient, amount)

    # Tokens are transferred from msg.sender (may be different from _recipient)
    self.erc20_safe_transferFrom(self.token.address, msg.sender, self, amount)

    return shares  # Just in case someone wants them


@view
@internal
def _shareValue(shares: uint256) -> uint256:
    # Determines the current value of `shares`.
        # NOTE: if sqrt(Vault.totalAssets()) >>> 1e39, this could potentially revert
    lockedFundsRatio: uint256 = (block.timestamp - self.lastReport) * self.lockedProfitDegration
    freeFunds: uint256 = self._totalAssets() 
    if(lockedFundsRatio < convert(1e18, uint256)):
        freeFunds = freeFunds - (self.lockedProfit - (lockedFundsRatio * self.lockedProfit / convert(1e18, uint256)))
    
    return (shares * freeFunds) / self.totalSupply

    
@view
@internal
def _sharesForAmount(amount: uint256) -> uint256:
    # Determines how many shares `amount` of token would receive.
    # See dev note on `deposit`.
    if self._totalAssets() > 0:
        # NOTE: if sqrt(token.totalSupply()) > 1e37, this could potentially revert
        return ((10 ** 3 * (amount * self.totalSupply)) / self._totalAssets()) / 10 ** 3
    else:
        return 0


@view
@external
def maxAvailableShares() -> uint256:
    """
    @notice
        Determines the maximum quantity of shares this Vault can facilitate a
        withdrawal for, factoring in assets currently residing in the Vault,
        as well as those deployed to strategies on the Vault's balance sheet.
    @dev
        Regarding how shares are calculated, see dev note on `deposit`.

        If you want to calculated the maximum a user could withdraw up to,
        you want to use this function.

        Note that the amount provided by this function is the theoretical
        maximum possible from withdrawing, the real amount depends on the
        realized losses incurred during withdrawal.
    @return The total quantity of shares this Vault can provide.
    """
    shares: uint256 = self._sharesForAmount(self.token.balanceOf(self))

    for strategy in self.withdrawalQueue:
        if strategy == ZERO_ADDRESS:
            break
        shares += self._sharesForAmount(self.strategies[strategy].totalDebt)

    return shares


@external
@nonreentrant("withdraw")
def withdraw(
    maxShares: uint256 = MAX_UINT256,
    recipient: address = msg.sender,
    maxLoss: uint256 = 1,  # 0.01% [BPS]
) -> uint256:
    """
    @notice
        Withdraws the calling account's tokens from this Vault, redeeming
        amount `_shares` for an appropriate amount of tokens.

        See note on `setWithdrawalQueue` for further details of withdrawal
        ordering and behavior.
    @dev
        Measuring the value of shares is based on the total outstanding debt
        that this contract has ("expected value") instead of the total balance
        sheet it has ("estimated value") has important security considerations,
        and is done intentionally. If this value were measured against external
        systems, it could be purposely manipulated by an attacker to withdraw
        more assets than they otherwise should be able to claim by redeeming
        their shares.

        On withdrawal, this means that shares are redeemed against the total
        amount that the deposited capital had "realized" since the point it
        was deposited, up until the point it was withdrawn. If that number
        were to be higher than the "expected value" at some future point,
        withdrawing shares via this method could entitle the depositor to
        *more* than the expected value once the "realized value" is updated
        from further reports by the Strategies to the Vaults.

        Under exceptional scenarios, this could cause earlier withdrawals to
        earn "more" of the underlying assets than Users might otherwise be
        entitled to, if the Vault's estimated value were otherwise measured
        through external means, accounting for whatever exceptional scenarios
        exist for the Vault (that aren't covered by the Vault's own design.)
    @param maxShares
        How many shares to try and redeem for tokens, defaults to all.
    @param recipient
        The address to issue the shares in this Vault to. Defaults to the
        caller's address.
    @param maxLoss
        The maximum acceptable loss to sustain on withdrawal. Defaults to 0.01%.
    @return The quantity of tokens redeemed for `_shares`.
    """
    shares: uint256 = maxShares  # May reduce this number below

    # If _shares not specified, transfer full share balance
    if shares == MAX_UINT256:
        shares = self.balanceOf[msg.sender]

    # Limit to only the shares they own
    assert shares <= self.balanceOf[msg.sender]

    # See @dev note, above.
    value: uint256 = self._shareValue(shares)

    totalLoss: uint256 = 0
    if value > self.token.balanceOf(self):
        # We need to go get some from our strategies in the withdrawal queue
        # NOTE: This performs forced withdrawals from each Strategy. During
        #       forced withdrawal, a Strategy may realize a loss. That loss
        #       is reported back to the Vault, and the will affect the amount
        #       of tokens that the withdrawer receives for their shares. They
        #       can optionally specify the maximum acceptable loss (in BPS)
        #       to prevent excessive losses on their withdrawals (which may
        #       happen in certain edge cases where Strategies realize a loss)
        for strategy in self.withdrawalQueue:
            if strategy == ZERO_ADDRESS:
                break  # We've exhausted the queue

            vault_balance: uint256 = self.token.balanceOf(self)
            if value <= vault_balance:
                break  # We're done withdrawing

            amountNeeded: uint256 = value - vault_balance

            # NOTE: Don't withdraw more than the debt so that Strategy can still
            #       continue to work based on the profits it has
            # NOTE: This means that user will lose out on any profits that each
            #       Strategy in the queue would return on next harvest, benefiting others
            amountNeeded = min(amountNeeded, self.strategies[strategy].totalDebt)
            if amountNeeded == 0:
                continue  # Nothing to withdraw from this Strategy, try the next one

            # Force withdraw amount from each Strategy in the order set by governance
            loss: uint256 = Strategy(strategy).withdraw(amountNeeded)
            withdrawn: uint256 = self.token.balanceOf(self) - vault_balance

            # NOTE: Withdrawer incurs any losses from liquidation
            if loss > 0:
                value -= loss
                totalLoss += loss
                self.strategies[strategy].totalLoss += loss

            # Reduce the Strategy's debt by the amount withdrawn ("realized returns")
            # NOTE: This doesn't add to returns as it's not earned by "normal means"
            self.strategies[strategy].totalDebt -= withdrawn + loss
            self.totalDebt -= withdrawn + loss

    # NOTE: We have withdrawn everything possible out of the withdrawal queue
    #       but we still don't have enough to fully pay them back, so adjust
    #       to the total amount we've freed up through forced withdrawals
    vault_balance: uint256 = self.token.balanceOf(self)
    if value > vault_balance:
        value = vault_balance
        # NOTE: Burn # of shares that corresponds to what Vault has on-hand,
        #       including the losses that were incurred above during withdrawals
        shares = self._sharesForAmount(value + totalLoss)

    # NOTE: This loss protection is put in place to revert if losses from
    #       withdrawing are more than what is considered acceptable.
    assert totalLoss <= maxLoss * (value + totalLoss) / MAX_BPS

    # Burn shares (full value of what is being withdrawn)
    self.totalSupply -= shares
    self.balanceOf[msg.sender] -= shares
    log Transfer(msg.sender, ZERO_ADDRESS, shares)

    # Withdraw remaining balance to _recipient (may be different to msg.sender) (minus fee)
    self.erc20_safe_transfer(self.token.address, recipient, value)

    return value


@view
@external
def pricePerShare() -> uint256:
    """
    @notice Gives the price for a single Vault share.
    @dev See dev note on `withdraw`.
    @return The value of a single share.
    """
    if self.totalSupply == 0:
        return 10 ** self.decimals  # price of 1:1
    else:
        return self._shareValue(10 ** self.decimals)


@internal
def _organizeWithdrawalQueue():
    # Reorganize `withdrawalQueue` based on premise that if there is an
    # empty value between two actual values, then the empty value should be
    # replaced by the later value.
    # NOTE: Relative ordering of non-zero values is maintained.
    offset: uint256 = 0
    for idx in range(MAXIMUM_STRATEGIES):
        strategy: address = self.withdrawalQueue[idx]
        if strategy == ZERO_ADDRESS:
            offset += 1  # how many values we need to shift, always `<= idx`
        elif offset > 0:
            self.withdrawalQueue[idx - offset] = strategy
            self.withdrawalQueue[idx] = ZERO_ADDRESS


@external
def addStrategy(
    strategy: address,
    debtRatio: uint256,
    minDebtPerHarvest: uint256,
    maxDebtPerHarvest: uint256,
    performanceFee: uint256,
):
    """
    @notice
        Add a Strategy to the Vault.

        This may only be called by governance.
    @dev
        The Strategy will be appended to `withdrawalQueue`, call
        `setWithdrawalQueue` to change the order.
    @param strategy The address of the Strategy to add.
    @param debtRatio
        The share of the total assets in the `vault that the `strategy` has access to.
    @param minDebtPerHarvest
        Lower limit on the increase of debt since last harvest
    @param maxDebtPerHarvest
        Upper limit on the increase of debt since last harvest
    @param performanceFee
        The fee the strategist will receive based on this Vault's performance.
    """
    # Check if queue is full
    assert self.withdrawalQueue[MAXIMUM_STRATEGIES - 1] == ZERO_ADDRESS

    # Check calling conditions
    assert not self.emergencyShutdown
    assert msg.sender == self.governance

    # Check strategy configuration
    assert strategy != ZERO_ADDRESS
    assert self.strategies[strategy].activation == 0
    assert self == Strategy(strategy).vault()
    assert self.token.address == Strategy(strategy).want()

    # Check strategy parameters
    assert self.debtRatio + debtRatio <= MAX_BPS
    assert minDebtPerHarvest <= maxDebtPerHarvest
    assert performanceFee <= MAX_BPS - self.performanceFee

    # Add strategy to approved strategies
    self.strategies[strategy] = StrategyParams({
        performanceFee: performanceFee,
        activation: block.timestamp,
        debtRatio: debtRatio,
        minDebtPerHarvest: minDebtPerHarvest,
        maxDebtPerHarvest: maxDebtPerHarvest,
        lastReport: block.timestamp,
        totalDebt: 0,
        totalGain: 0,
        totalLoss: 0,
    })
    log StrategyAdded(strategy, debtRatio, minDebtPerHarvest, maxDebtPerHarvest, performanceFee)

    # Update Vault parameters
    self.debtRatio += debtRatio

    # Add strategy to the end of the withdrawal queue
    self.withdrawalQueue[MAXIMUM_STRATEGIES - 1] = strategy
    self._organizeWithdrawalQueue()


@external
def updateStrategyDebtRatio(
    strategy: address,
    debtRatio: uint256,
):
    """
    @notice
        Change the quantity of assets `strategy` may manage.

        This may be called by governance or management.
    @param strategy The Strategy to update.
    @param debtRatio The quantity of assets `strategy` may now manage.
    """
    assert msg.sender in [self.management, self.governance]
    assert self.strategies[strategy].activation > 0
    self.debtRatio -= self.strategies[strategy].debtRatio
    self.strategies[strategy].debtRatio = debtRatio
    self.debtRatio += debtRatio
    assert self.debtRatio <= MAX_BPS
    log StrategyUpdateDebtRatio(strategy, debtRatio)


@external
def updateStrategyMinDebtPerHarvest(
    strategy: address,
    minDebtPerHarvest: uint256,
):
    """
    @notice
        Change the quantity assets per block this Vault may deposit to or
        withdraw from `strategy`.

        This may only be called by governance or management.
    @param strategy The Strategy to update.
    @param minDebtPerHarvest
        Lower limit on the increase of debt since last harvest
    """
    assert msg.sender in [self.management, self.governance]
    assert self.strategies[strategy].activation > 0
    assert self.strategies[strategy].maxDebtPerHarvest >= minDebtPerHarvest
    self.strategies[strategy].minDebtPerHarvest = minDebtPerHarvest
    log StrategyUpdateMinDebtPerHarvest(strategy, minDebtPerHarvest)


@external
def updateStrategyMaxDebtPerHarvest(
    strategy: address,
    maxDebtPerHarvest: uint256,
):
    """
    @notice
        Change the quantity assets per block this Vault may deposit to or
        withdraw from `strategy`.

        This may only be called by governance or management.
    @param strategy The Strategy to update.
    @param maxDebtPerHarvest
        Upper limit on the increase of debt since last harvest
    """
    assert msg.sender in [self.management, self.governance]
    assert self.strategies[strategy].activation > 0
    assert self.strategies[strategy].minDebtPerHarvest <= maxDebtPerHarvest
    self.strategies[strategy].maxDebtPerHarvest = maxDebtPerHarvest
    log StrategyUpdateMaxDebtPerHarvest(strategy, maxDebtPerHarvest)


@external
def updateStrategyPerformanceFee(
    strategy: address,
    performanceFee: uint256,
):
    """
    @notice
        Change the fee the strategist will receive based on this Vault's
        performance.

        This may only be called by governance.
    @param strategy The Strategy to update.
    @param performanceFee The new fee the strategist will receive.
    """
    assert msg.sender == self.governance
    assert performanceFee <= MAX_BPS - self.performanceFee
    assert self.strategies[strategy].activation > 0
    self.strategies[strategy].performanceFee = performanceFee
    log StrategyUpdatePerformanceFee(strategy, performanceFee)


@internal
def _revokeStrategy(strategy: address):
    self.debtRatio -= self.strategies[strategy].debtRatio
    self.strategies[strategy].debtRatio = 0
    log StrategyRevoked(strategy)


@external
def migrateStrategy(oldVersion: address, newVersion: address):
    """
    @notice
        Migrates a Strategy, including all assets from `oldVersion` to
        `newVersion`.

        This may only be called by governance.
    @dev
        Strategy must successfully migrate all capital and positions to new
        Strategy, or else this will upset the balance of the Vault.

        The new Strategy should be "empty" e.g. have no prior commitments to
        this Vault, otherwise it could have issues.
    @param oldVersion The existing Strategy to migrate from.
    @param newVersion The new Strategy to migrate to.
    """
    assert msg.sender == self.governance
    assert newVersion != ZERO_ADDRESS
    assert self.strategies[oldVersion].activation > 0
    assert self.strategies[newVersion].activation == 0

    strategy: StrategyParams = self.strategies[oldVersion]

    self._revokeStrategy(oldVersion)
    # _revokeStrategy will lower the debtRatio
    self.debtRatio += strategy.debtRatio
    # Debt is migrated to new strategy
    self.strategies[oldVersion].totalDebt = 0

    self.strategies[newVersion] = StrategyParams({
        performanceFee: strategy.performanceFee,
        # NOTE: use last report for activation time, so E[R] calc works
        activation: strategy.lastReport,
        debtRatio: strategy.debtRatio,
        minDebtPerHarvest: strategy.minDebtPerHarvest,
        maxDebtPerHarvest: strategy.maxDebtPerHarvest,
        lastReport: strategy.lastReport,
        totalDebt: strategy.totalDebt,
        totalGain: 0,
        totalLoss: 0,
    })

    Strategy(oldVersion).migrate(newVersion)
    log StrategyMigrated(oldVersion, newVersion)

    for idx in range(MAXIMUM_STRATEGIES):
        if self.withdrawalQueue[idx] == oldVersion:
            self.withdrawalQueue[idx] = newVersion
            return  # Don't need to reorder anything because we swapped


@external
def revokeStrategy(strategy: address = msg.sender):
    """
    @notice
        Revoke a Strategy, setting its debt limit to 0 and preventing any
        future deposits.

        This function should only be used in the scenario where the Strategy is
        being retired but no migration of the positions are possible, or in the
        extreme scenario that the Strategy needs to be put into "Emergency Exit"
        mode in order for it to exit as quickly as possible. The latter scenario
        could be for any reason that is considered "critical" that the Strategy
        exits its position as fast as possible, such as a sudden change in market
        conditions leading to losses, or an imminent failure in an external
        dependency.

        This may only be called by governance, the guardian, or the Strategy
        itself. Note that a Strategy will only revoke itself during emergency
        shutdown.
    @param strategy The Strategy to revoke.
    """
    assert msg.sender in [strategy, self.governance, self.guardian]
    self._revokeStrategy(strategy)


@external
def addStrategyToQueue(strategy: address):
    """
    @notice
        Adds `strategy` to `withdrawalQueue`.

        This may only be called by governance or management.
    @dev
        The Strategy will be appended to `withdrawalQueue`, call
        `setWithdrawalQueue` to change the order.
    @param strategy The Strategy to add.
    """
    assert msg.sender in [self.management, self.governance]
    # Must be a current Strategy
    assert self.strategies[strategy].activation > 0
    # Check if queue is full
    assert self.withdrawalQueue[MAXIMUM_STRATEGIES - 1] == ZERO_ADDRESS
    # Can't already be in the queue
    for s in self.withdrawalQueue:
        if strategy == ZERO_ADDRESS:
            break
        assert s != strategy
    self.withdrawalQueue[MAXIMUM_STRATEGIES - 1] = strategy
    self._organizeWithdrawalQueue()
    log StrategyAddedToQueue(strategy)


@external
def removeStrategyFromQueue(strategy: address):
    """
    @notice
        Remove `strategy` from `withdrawalQueue`.

        This may only be called by governance or management.
    @dev
        We don't do this with revokeStrategy because it should still
        be possible to withdraw from the Strategy if it's unwinding.
    @param strategy The Strategy to remove.
    """
    assert msg.sender in [self.management, self.governance]
    for idx in range(MAXIMUM_STRATEGIES):
        if self.withdrawalQueue[idx] == strategy:
            self.withdrawalQueue[idx] = ZERO_ADDRESS
            self._organizeWithdrawalQueue()
            log StrategyRemovedFromQueue(strategy)
            return  # We found the right location and cleared it
    raise  # We didn't find the Strategy in the queue


@view
@internal
def _debtOutstanding(strategy: address) -> uint256:
    # See note on `debtOutstanding()`.
    strategy_debtLimit: uint256 = self.strategies[strategy].debtRatio * self._totalAssets() / MAX_BPS
    strategy_totalDebt: uint256 = self.strategies[strategy].totalDebt

    if self.emergencyShutdown:
        return strategy_totalDebt
    elif strategy_totalDebt <= strategy_debtLimit:
        return 0
    else:
        return strategy_totalDebt - strategy_debtLimit


@view
@external
def debtOutstanding(strategy: address = msg.sender) -> uint256:
    """
    @notice
        Determines if `strategy` is past its debt limit and if any tokens
        should be withdrawn to the Vault.
    @param strategy The Strategy to check. Defaults to the caller.
    @return The quantity of tokens to withdraw.
    """
    return self._debtOutstanding(strategy)


@view
@internal
def _creditAvailable(strategy: address) -> uint256:
    # See note on `creditAvailable()`.
    if self.emergencyShutdown:
        return 0

    vault_totalAssets: uint256 = self._totalAssets()
    vault_debtLimit: uint256 = self.debtRatio * vault_totalAssets / MAX_BPS
    vault_totalDebt: uint256 = self.totalDebt
    strategy_debtLimit: uint256 = self.strategies[strategy].debtRatio * vault_totalAssets / MAX_BPS
    strategy_totalDebt: uint256 = self.strategies[strategy].totalDebt
    strategy_minDebtPerHarvest: uint256 = self.strategies[strategy].minDebtPerHarvest
    strategy_maxDebtPerHarvest: uint256 = self.strategies[strategy].maxDebtPerHarvest

    # Exhausted credit line
    if strategy_debtLimit <= strategy_totalDebt or vault_debtLimit <= vault_totalDebt:
        return 0

    # Start with debt limit left for the Strategy
    available: uint256 = strategy_debtLimit - strategy_totalDebt

    # Adjust by the global debt limit left
    available = min(available, vault_debtLimit - vault_totalDebt)

    # Can only borrow up to what the contract has in reserve
    # NOTE: Running near 100% is discouraged
    available = min(available, self.token.balanceOf(self))

    # Adjust by min and max borrow limits (per harvest)
    # NOTE: min increase can be used to ensure that if a strategy has a minimum
    #       amount of capital needed to purchase a position, it's not given capital
    #       it can't make use of yet.
    # NOTE: max increase is used to make sure each harvest isn't bigger than what
    #       is authorized. This combined with adjusting min and max periods in
    #       `BaseStrategy` can be used to effect a "rate limit" on capital increase.
    if available < strategy_minDebtPerHarvest:
        return 0
    else:
        return min(available, strategy_maxDebtPerHarvest)

@view
@external
def creditAvailable(strategy: address = msg.sender) -> uint256:
    """
    @notice
        Amount of tokens in Vault a Strategy has access to as a credit line.

        This will check the Strategy's debt limit, as well as the tokens
        available in the Vault, and determine the maximum amount of tokens
        (if any) the Strategy may draw on.

        In the rare case the Vault is in emergency shutdown this will return 0.
    @param strategy The Strategy to check. Defaults to caller.
    @return The quantity of tokens available for the Strategy to draw on.
    """
    return self._creditAvailable(strategy)


@view
@internal
def _expectedReturn(strategy: address) -> uint256:
    # See note on `expectedReturn()`.
    strategy_lastReport: uint256 = self.strategies[strategy].lastReport
    timeSinceLastHarvest: uint256 = block.timestamp - strategy_lastReport
    totalHarvestTime: uint256 = strategy_lastReport - self.strategies[strategy].activation

    # NOTE: If either `timeSinceLastHarvest` or `totalHarvestTime` is 0, we can short-circuit to `0`
    if timeSinceLastHarvest > 0 and totalHarvestTime > 0 and Strategy(strategy).isActive():
        # NOTE: Unlikely to throw unless strategy accumalates >1e68 returns
        # NOTE: Calculate average over period of time where harvests have occured in the past
        return (self.strategies[strategy].totalGain * timeSinceLastHarvest) / totalHarvestTime
    else:
        return 0  # Covers the scenario when block.timestamp == activation


@view
@external
def availableDepositLimit() -> uint256:
    if self.depositLimit > self._totalAssets():
        return self.depositLimit - self._totalAssets()
    else:
        return 0


@view
@external
def expectedReturn(strategy: address = msg.sender) -> uint256:
    """
    @notice
        Provide an accurate expected value for the return this `strategy`
        would provide to the Vault the next time `report()` is called
        (since the last time it was called).
    @param strategy The Strategy to determine the expected return for. Defaults to caller.
    @return
        The anticipated amount `strategy` should make on its investment
        since its last report.
    """
    return self._expectedReturn(strategy)


@internal
def _reportLoss(strategy: address, loss: uint256):
    # Loss can only be up the amount of debt issued to strategy
    totalDebt: uint256 = self.strategies[strategy].totalDebt
    assert totalDebt >= loss
    self.strategies[strategy].totalLoss += loss
    self.strategies[strategy].totalDebt = totalDebt - loss
    self.totalDebt -= loss

    # Also, make sure we reduce our trust with the strategy by the same amount
    debtRatio: uint256 = self.strategies[strategy].debtRatio
    ratio_change: uint256 = min(loss * MAX_BPS / self._totalAssets(), debtRatio)
    self.strategies[strategy].debtRatio -= ratio_change 
    self.debtRatio -= ratio_change

@internal
def _assessFees(strategy: address, gain: uint256):
    # Issue new shares to cover fees
    # NOTE: In effect, this reduces overall share price by the combined fee
    # NOTE: may throw if Vault.totalAssets() > 1e64, or not called for more than a year
    governance_fee: uint256 = (
        (self.totalDebt * (block.timestamp - self.lastReport) * self.managementFee)
        / MAX_BPS
        / SECS_PER_YEAR
    )
    strategist_fee: uint256 = 0  # Only applies in certain conditions

    # NOTE: Applies if Strategy is not shutting down, or it is but all debt paid off
    # NOTE: No fee is taken when a Strategy is unwinding it's position, until all debt is paid
    if gain > 0:
        # NOTE: Unlikely to throw unless strategy reports >1e72 harvest profit
        strategist_fee = (
            gain * self.strategies[strategy].performanceFee
        ) / MAX_BPS
        # NOTE: Unlikely to throw unless strategy reports >1e72 harvest profit
        governance_fee += gain * self.performanceFee / MAX_BPS

    # NOTE: This must be called prior to taking new collateral,
    #       or the calculation will be wrong!
    # NOTE: This must be done at the same time, to ensure the relative
    #       ratio of governance_fee : strategist_fee is kept intact
    total_fee: uint256 = governance_fee + strategist_fee
    if total_fee > 0:  # NOTE: If mgmt fee is 0% and no gains were realized, skip
        reward: uint256 = self._issueSharesForAmount(self, total_fee)

        # Send the rewards out as new shares in this Vault
        if strategist_fee > 0:  # NOTE: Guard against DIV/0 fault
            # NOTE: Unlikely to throw unless sqrt(reward) >>> 1e39
            strategist_reward: uint256 = (strategist_fee * reward) / total_fee
            self._transfer(self, strategy, strategist_reward)
            # NOTE: Strategy distributes rewards at the end of harvest()
        # NOTE: Governance earns any dust leftover from flooring math above
        if self.balanceOf[self] > 0:
            self._transfer(self, self.rewards, self.balanceOf[self])


@external
def report(gain: uint256, loss: uint256, _debtPayment: uint256) -> uint256:
    """
    @notice
        Reports the amount of assets the calling Strategy has free (usually in
        terms of ROI).

        The performance fee is determined here, off of the strategy's profits
        (if any), and sent to governance.

        The strategist's fee is also determined here (off of profits), to be
        handled according to the strategist on the next harvest.

        This may only be called by a Strategy managed by this Vault.
    @dev
        For approved strategies, this is the most efficient behavior.
        The Strategy reports back what it has free, then Vault "decides"
        whether to take some back or give it more. Note that the most it can
        take is `gain + _debtPayment`, and the most it can give is all of the
        remaining reserves. Anything outside of those bounds is abnormal behavior.

        All approved strategies must have increased diligence around
        calling this function, as abnormal behavior could become catastrophic.
    @param gain
        Amount Strategy has realized as a gain on it's investment since its
        last report, and is free to be given back to Vault as earnings
    @param loss
        Amount Strategy has realized as a loss on it's investment since its
        last report, and should be accounted for on the Vault's balance sheet
    @param _debtPayment
        Amount Strategy has made available to cover outstanding debt
    @return Amount of debt outstanding (if totalDebt > debtLimit or emergency shutdown).
    """

    # Only approved strategies can call this function
    assert self.strategies[msg.sender].activation > 0
    # No lying about total available to withdraw!
    assert self.token.balanceOf(msg.sender) >= gain + _debtPayment

    # We have a loss to report, do it before the rest of the calculations
    if loss > 0:
        self._reportLoss(msg.sender, loss)

    # Assess both management fee and performance fee, and issue both as shares of the vault
    self._assessFees(msg.sender, gain)

    # Returns are always "realized gains"
    self.strategies[msg.sender].totalGain += gain

    # Outstanding debt the Strategy wants to take back from the Vault (if any)
    # NOTE: debtOutstanding <= StrategyParams.totalDebt
    debt: uint256 = self._debtOutstanding(msg.sender)
    debtPayment: uint256 = min(_debtPayment, debt)

    if debtPayment > 0:
        self.strategies[msg.sender].totalDebt -= debtPayment
        self.totalDebt -= debtPayment
        debt -= debtPayment
        # NOTE: `debt` is being tracked for later

    # Compute the line of credit the Vault is able to offer the Strategy (if any)
    credit: uint256 = self._creditAvailable(msg.sender)

    # Update the actual debt based on the full credit we are extending to the Strategy
    # or the returns if we are taking funds back
    # NOTE: credit + self.strategies[msg.sender].totalDebt is always < self.debtLimit
    # NOTE: At least one of `credit` or `debt` is always 0 (both can be 0)
    if credit > 0:
        self.strategies[msg.sender].totalDebt += credit
        self.totalDebt += credit

    # Give/take balance to Strategy, based on the difference between the reported gains
    # (if any), the debt payment (if any), the credit increase we are offering (if any),
    # and the debt needed to be paid off (if any)
    # NOTE: This is just used to adjust the balance of tokens between the Strategy and
    #       the Vault based on the Strategy's debt limit (as well as the Vault's).
    totalAvail: uint256 = gain + debtPayment
    if totalAvail < credit:  # credit surplus, give to Strategy
        self.erc20_safe_transfer(self.token.address, msg.sender, credit - totalAvail)
    elif totalAvail > credit:  # credit deficit, take from Strategy
        self.erc20_safe_transferFrom(self.token.address, msg.sender, self, totalAvail - credit)
    # else, don't do anything because it is balanced

    # Update reporting time
    self.strategies[msg.sender].lastReport = block.timestamp
    self.lastReport = block.timestamp
    self.lockedProfit = gain # profit is locked and gradually released per block

    log StrategyReported(
        msg.sender,
        gain,
        loss,
        debtPayment,
        self.strategies[msg.sender].totalGain,
        self.strategies[msg.sender].totalLoss,
        self.strategies[msg.sender].totalDebt,
        credit,
        self.strategies[msg.sender].debtRatio,
    )

    if self.strategies[msg.sender].debtRatio == 0 or self.emergencyShutdown:
        # Take every last penny the Strategy has (Emergency Exit/revokeStrategy)
        # NOTE: This is different than `debt` in order to extract *all* of the returns
        return Strategy(msg.sender).estimatedTotalAssets()
    else:
        # Otherwise, just return what we have as debt outstanding
        return debt


@external
def sweep(token: address, amount: uint256 = MAX_UINT256):
    """
    @notice
        Removes tokens from this Vault that are not the type of token managed
        by this Vault. This may be used in case of accidentally sending the
        wrong kind of token to this Vault.

        Tokens will be sent to `governance`.

        This will fail if an attempt is made to sweep the tokens that this
        Vault manages.

        This may only be called by governance.
    @param token The token to transfer out of this vault.
    @param amount The quantity or tokenId to transfer out.
    """
    assert msg.sender == self.governance
    # Can't be used to steal what this Vault is protecting
    assert token != self.token.address
    value: uint256 = amount
    if value == MAX_UINT256:
        value = ERC20(token).balanceOf(self)
    self.erc20_safe_transfer(token, self.governance, value)
