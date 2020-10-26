# Yearn System Specification

## Definitions

- Governance: YFI token governance system
- Treasury: Yearn rewards mechanism/protocol dev fund
- Vault: Only user touch-point, manages funds
- Strategy: Complex external interactions w/ limited access to Vault

## Vault Specification

### Definitions

- Guardian: Trusted with privileged access for limited operations (ensuring safety of Vaults)

### Normal Operation

NOTE: Users should only withdraw "free" assets as some strategies need to divest "gracefully", and a large withdrawal could negatively affect the position of connected strategies.

NOTE: "free" assets in the Vault means the amount the Vault has freely available (e.g. not invested in Strategies)

1. A User is able to deposit any amount of the single asset the Vault accepts in exchange for shares of the Vault's underlying assets.
2. A User is able to withdraw an amount of their shares up to the "free" deposits that the Vault has not lent out with no additional fee.
3. A User is able to withdraw an amount of their shares above and beyond the "free" deposits that the Vault has not lent out with an additional fee based on the amount forcibly withdrawn from the Vault's Strategies.
4. A User is able to transfer any amount of Vault shares to anyone else.
5. Only Governance can approve Strategies to interact with Vaults and take on debt.
6. Only Governance can increase the parameters of a Strategy's borrowing limit.
7. Only Governance can migrate a Strategy, and their current capital and debt, to a newer version of the Strategy.
8. Governance can set the Guardian role to another account, without their permission
9. Either the Guardian or Governance can revoke a Strategy from borrowing any more assets from the Strategy.
10. Either the Guardian or Governance can trigger the Vault to enter Emergency Shutdown Mode

### Fees

- The Treasury (which benefits Governance) collects a "performance fee" based on the amount of returns a Strategy produces during Normal Operation, assessed each time the Strategy interacts with the Vault, and is provided as newly minted shares to the Treasury
- Each Strategist collects a "performance fee" based on the amount of returns their Strategy produces during Normal Operation, assessed each time the Strategy interacts with the Vault, and is provided as newly minted shares to the Strategist
- A "withdrawal fee" is assessed each time a User withdraws more than the Vault has "freely" available, which is assessed as a penalty paid to both the Treasury and each Strategist affected depending on the amount withdrawn.

### Emergency Shutdown Mode

NOTE: During Emergency Shutdown mode of the Vault, the intention is for the Vault to recall the debt as quickly as reasonable (given on-chain conditions) with minimal losses, and open up deposits to be withdrawn by Users as easily as possible. There is no restrictions on withdrawals above what is expected under Normal Operation.

1. During Emergency Shutdown, no Users may deposit into the Vault
2. During Emergency Shutdown, Governance cannot add new Strategies
3. During Emergency Shutdown, each Strategy must pay back their debt as quickly as reasonable to minimally affect their position
4. Only Governance can undo Emergency Shutdown

## Strategy Specification

### Definitions

- Strategist: original creator of strategy, is in charge of monitoring its position for adverse effects.
- Keeper: a bot which maintains the strategy, by ensuring it regularly generates returns for the Vault during pre-defined intervals or events

### Normal Operation

NOTE: Triggers must be defined for the interval(s) allowable without causing instability to the Strategy's position

NOTE: Updates must not trigger an instability in the Vault, especially when considering other Strategies' update rates

1. The Strategy can interact with its connected Vault, and obtain capital according to its current borrowing limit
2. The Strategy can interact with any external system required to turn the capital borrowed into returns for the Vault
3. The Strategy defines triggers for either Governance, the Strategist, or the Keeper to update or adjust its position(s), based on on-chain activity, the synchronization frequency, and externalized gas costs
4. The Vault can migrate the debt and positions of the Strategy to a newer version of that strategy
5. Either Governance or the Strategist can trigger Emergency Exit Mode

### Emergency Exit Mode

NOTE: In this mode, the Strategy defines a reversionary position that seeks to unwind and divest funds back to the Vault as quickly and smoothly as possible, with up to a nominal amount of slippage expected

1. During Emergency Exit, the Strategy does not pull more funds from the connected Vault
2. During Emergency Exit, the Strategy can still interact with any external system, but must be able to handle a failure of that system as best as it can manage
4. Only Governance can undo Emergency Exit

## Governance Specification

NOTE: Governance is expected to manage each deployed Vault and the strategies connected to them in order to maintain the risk and returns that Vault users expect

1. Governance must be able to perform the calls expected for it to manage the Vaults and Strategies it maintains within a reasonable timeframe in order to maintain safe operation of the system.

## Treasury Specification

NOTE: Rewards are given as shares of each Vault, which are redeemable for the underlying token that the Vault is wrapping.

NOTE: It is up to the design of the Treasury to unwrap and further account for the share of the underlying awarded to governance participants, and the other parties in the Yearn ecosystem (including keeper gas fees, protocol development and maintenance costs, etc.)

NOTE: The Treasury system could leverage the Vault design, with strategies that just market sell the rewards for YFI.

*There are no direct requirements for the Treasury in this Specification*
