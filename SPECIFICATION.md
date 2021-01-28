# Yearn System Specification

## Definitions

- Governance: YFI token governance system
- Treasury: Yearn rewards mechanism/protocol dev fund
- Vault: Only user touch-point, manages funds
- Strategy: Complex external interactions w/ limited access to Vault
- Strategist: original creator of strategy, is in charge of monitoring its position for adverse effects.
- Registry: On-chain registry of deployed Vaults for tokens, indexed by API version

## Vault Specification

### Definitions

- Management: Trusted with privledged access for limited operations (ensuring performance of Vaults)
- Guardian: Trusted with privileged access for limited operations (ensuring safety of Vaults)

### Normal Operation

NOTE: Users should only withdraw "free" assets as some strategies need to divest "gracefully", and a large withdrawal could incur a loss, which will get passed back to the withdrawer.

NOTE: "free" assets in the Vault means the amount the Vault has freely available (e.g. not invested in Strategies)

NOTE: The strategy can also revoke itself during normal operation of the Vault, but this behavior only occurs during "Emergency Exit" mode.

1. A User is able to deposit an amount of the single asset the Vault accepts in exchange for shares of the Vault's underlying assets, depending on the Vault's deposit configuration.
1. A User is able to withdraw an amount of tokens represented by their shares up to the total available amount that can be withdrawn from the combination of the Vault's overhead, and what can be forcibly withdrawn from all the strategies with debt to the Vault that have been pre-authorized for withdrawals in the Vault's withdrawal queue.
1. A User is able to transfer any amount of their Vault shares to anyone else.
1. Only Governance can approve Strategies to interact with Vaults and take on debt.
1. Governance can set the Management role to another account, without their permission.
1. Either Governance or Management can modify the parameters of a Strategy's borrowing capabilities.
1. Either Governance or Management can reconfigure the strategies in the withdrawal queue.
1. Only Governance can migrate a Strategy, and their current capital and debt, to a newer version of the Strategy.
1. Governance can set the Guardian role to another account, without their permission.
1. Either the Guardian or Governance can revoke a Strategy from borrowing any more assets from the Vault and trigger a divestment of that Strategy.
1. Either the Guardian or Governance can trigger the Vault to enter Emergency Shutdown Mode and trigger a divestment from all connected Strategies.

### Fees

1. The Treasury (which benefits Governance) collects a "management fee" based on the total assets the Vault has over a period of time, assessed each time the Strategy interacts with the Vault, and is provided as newly minted shares to the Treasury.
1. The Treasury (which benefits Governance) collects a "performance fee" based on the amount of returns a Strategy produces during Normal Operation, assessed each time the Strategy interacts with the Vault, and is provided as newly minted shares to the Treasury.
1. Each Strategist collects a "performance fee" based on the amount of positive returns their Strategy produces during Normal Operation, assessed each time the Strategy interacts with the Vault, and is provided as newly minted shares to the Strategist.

### Emergency Shutdown Mode

NOTE: During Emergency Shutdown mode of the Vault, the intention is for the Vault to recall the debt as quickly as reasonable (given on-chain conditions) with minimal losses, and open up deposits to be withdrawn by Users as easily as possible. There is no restrictions on withdrawals above what is expected under Normal Operation.

1. During Emergency Shutdown, no Users may deposit into the Vault.
1. During Emergency Shutdown, Governance cannot add new Strategies.
1. During Emergency Shutdown, the Vault should communicate to each Strategy to return their entire position as quickly as reasonable, with minimal impact to their positions (Normal Operation).
1. Only Governance can exit Emergency Shutdown Mode.

## Strategy Specification

### Definitions

- Keeper: a bot which maintains the strategy, by ensuring it regularly generates returns for the Vault during pre-defined intervals or events

### Normal Operation

NOTE: Triggers must be defined for the interval(s) allowable without causing instability to the Strategy's position

NOTE: Updates must not trigger an instability in the Vault, especially when considering other Strategies' update frequencies

1. The Strategy can interact with its connected Vault, and obtain capital according to its current borrowing limit.
1. The Strategy can interact with any external system required to turn the capital borrowed into returns for the Vault
1. The Strategy defines triggers for either Governance, the Strategist, or the Keeper to use as a signal to update or adjust its position(s).
1. The Strategy defines triggers for either Governance, the Strategist, or the Keeper to use as a signal to take profits and report to the Vault.
1. Either Governance or the Vault can migrate the positions of the Strategy to another Strategy.
1. Either Governance or the Strategist can trigger the Strategy to enter into Emergency Exit Mode.

### Emergency Exit Mode

NOTE: In this mode, the Strategy defines a reversionary set of actions that seek to unwind and divest funds back to the Vault as quickly and smoothly as possible, with as minimal losses as possible.

1. During Emergency Exit, the Strategy cannot take new debt from the connected Vault.
1. During Emergency Exit, the Strategy can still interact with any external system, but must be able to handle any failure(s) of each of those system(s) as well as possible.
1. There is no condition that can revert Emergency Exit Mode once it is entered.

## Registry Specification

### Normal Operation

NOTE: The Registry allows an on-chain reference for Vault deployment events, to be used with external integrations. It is also possible to reconstruct the deployment and release history via on-chain calls.

NOTE: The API version of each Vault deployment for a token should increase according to [Semantic Versioning](https://semver.org/). However, this is not practically enforced.

1. Only Governance can register a new release for future Vaults to use when deploying via proxy deployment.
1. Anyone can deploy a proxy deployment Vault, using the latest release, for experimental purposes
1. Only Governance can endorse a Vault deployment for a given token with the latest release.

## Governance Specification

NOTE: Governance is expected to manage each deployed Vault and the strategies connected to them in order to maintain the risk and returns that Vault users expect

1. Governance must be able to perform the calls expected for it to manage the Vaults and Strategies it maintains.
1. Any actions that require the exclusive action by Governance must be able to be accomplished safely within a reasonable timeframe.

## Treasury Specification

NOTE: Rewards are given as shares of each Vault, which are redeemable for the underlying token that the Vault is wrapping.

NOTE: It is up to the design of the Treasury to unwrap and further account for the share of the underlying awarded to governance participants, and the other parties in the Yearn ecosystem (including keeper gas fees, protocol development and maintenance costs, etc.)

NOTE: The Treasury system could leverage the Vault design, with strategies that just market sell the rewards for YFI.

1. The Treasury should incentivize proper management of the Vault by Governance, optimizing for stability of returns over long periods of time, minimizing risk, and encouraging growth of deposits.
