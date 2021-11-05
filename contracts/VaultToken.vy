# @version 0.2.16

API_VERSION: constant(String[28]) = "0.5.0"

vault: public(address)
gov: public(address)

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

decimals: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])
totalSupply: public(uint256)

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_SEPARATOR: public(bytes32)
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

interface IVaultAPI:
    def token() -> address: view
    def vault_token() -> address: view
    def decimals() -> uint256: view
    def vaultToken() -> address: view

@external
def __init__(
    gov: address,
    decimals: uint256
):
    self.gov = gov
    self.decimals = decimals
    # EIP-712
    self.DOMAIN_SEPARATOR = keccak256(
        concat(
            DOMAIN_TYPE_HASH,
            keccak256(convert("Yearn Vault", Bytes[11])),
            keccak256(convert(API_VERSION, Bytes[28])),
            convert(chain.id, bytes32),
            convert(self, bytes32)
        ))

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
def setVault(vault: address):
    assert (msg.sender == self.vault or (msg.sender == self.gov and self.vault == ZERO_ADDRESS)) # gov
    assert IVaultAPI(vault).decimals() == self.decimals # decimals
    assert IVaultAPI(vault).vault_token() == self # !vault_token
    self.vault = vault

@internal
def _transfer(sender: address, receiver: address, amount: uint256):
    # See note on `transfer()`.

    # Protect people from accidentally sending their shares to bad places
    assert receiver not in [self, self.vault, ZERO_ADDRESS]
    self.balanceOf[sender] -= amount
    self.balanceOf[receiver] += amount
    log Transfer(sender, receiver, amount)

@external
def transfer(sender: address, receiver: address, amount: uint256) -> bool:
    assert msg.sender == self.vault
    self._transfer(sender, receiver, amount)
    return True

@external
def transferFrom(sender: address, operator: address, receiver: address, amount: uint256) -> bool:
    assert msg.sender == self.vault

    # Unlimited approval (saves an SSTORE)
    if (self.allowance[sender][operator] < MAX_UINT256):
        allowance: uint256 = self.allowance[sender][operator] - amount
        self.allowance[sender][operator] = allowance
        # NOTE: Allows log filters to have a full accounting of allowance changes
        log Approval(sender, operator, allowance)
    self._transfer(sender, receiver, amount)
    return True

@external
def approve(owner: address, spender: address, amount: uint256) -> bool:
    assert msg.sender == self.vault

    self.allowance[owner][spender] = amount
    return True

@external
def increaseAllowance(owner: address, spender: address, amount: uint256) -> bool:
    assert msg.sender == self.vault

    self.allowance[owner][spender] += amount
    log Approval(owner, spender, self.allowance[owner][spender])

    return True

@external
def decreaseAllowance(owner: address, spender: address, amount: uint256) -> bool:
    assert msg.sender == self.vault

    self.allowance[owner][spender] -= amount
    log Approval(owner, spender, self.allowance[owner][spender])
    return True

@external
def mint(shares: uint256, account: address) -> bool:
    assert msg.sender == self.vault

    self.totalSupply +=  shares
    self.balanceOf[account] += shares
    log Transfer(ZERO_ADDRESS, account, shares)
    return True

@external
def burn(shares: uint256, account: address) -> bool:
    assert msg.sender == self.vault

    self.totalSupply -= shares
    self.balanceOf[account] -= shares
    log Transfer(account, ZERO_ADDRESS, shares)
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
