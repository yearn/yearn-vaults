# Deploy a Strategy / Vault for V2

NOTE: This repo is encouraged to create multiple scripts for governance and dev multisig execution of complex transactions
https://github.com/iearn-finance/chief-multisig-officer

**IMPORTANT**: you should **NOT** create a new release with a test vault

## Before deploying
- Coordinate with Core Dev strategist for getting a review in board https://github.com/orgs/iearn-finance/projects/5
- Peer review completed by:
    - yearn.rocks / Experimental: at least 2 strategists
- Check if want token has a deploy vault already (>=v0.3.0) and coordinate to use that first if possible.
- If a new vault is needed, deploy it using the registry:
    - `registry.newExperimentalVault(want, you, multisig, treasury, "", "")`
        - args: token, gov, guardian, rewards, name, symbol
        - multisig (strategists) = '0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7'
        - gov for testing = '0x846e211e8ba920b353fb717631c015cf04061cc9' (dev.ychad.eth) 
        - treasury = '0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde'
        (treasury.ychad.eth)
    - Check new vault has ABI setup on etherscan (until verification with Vyper and proxy is fixed on Etherscan)
    - Coordinate with a core developer to stablish proper deposit limit for new vault and other settings. See the table below: [Limits per Stage](#Limits per Stage)
    - Set a deposit limit to the vault
    `vault.setDepositLimit(50_000 * 1e18)`
    $50k USD converted to your want. Example above is 50k DAI
- Deploy strategy with settings and upload code to Etherscan for verification
- Tag GitHub review issue https://github.com/orgs/iearn-finance/projects/5 with deployed version and add mainnet address(es).

## After deploying strategy
- Add strategy to vault
    - `vault.addStrategy(strategy, debt_ratio, rate_limit, 1000)`
    - debt_ratio should be 9800 if first strategy on vault
    - rate_limit is 0 unless there is reason for it to be different
- Set keeper
    - `strategy.setKeeper(keep3r_manager)`
    - keep3r_manager = '0x13dAda6157Fee283723c0254F43FF1FdADe4EEd6'
- Set rewards
    - `strategy.setRewards(address)`
    Read below if you want to use the sharer contract
- Set management fee to 0
    - `vault.setManagementFee(0)`
- Set governance
    - `vault.setGovernance(multisig)`
    - multisig = '0x846e211e8ba920b353fb717631c015cf04061cc9'
    (dev.ychad.eth)
    - Governance needs to be accepted before it is in place. After you set this you will still have control over the strategy.
- Run tests against "live" vault and strategy in mainnet-fork
    - Harvest
    - Profitable harvest
    - Revoke strategy and check that funds return to the vault
    - Increase/decrease debt + harvest, and check that the strategy is working well
    - Migration
    - Check that tokens in the strategy cannot be sweeped by dust collection

   Example: https://github.com/Macarse/yhegic/tree/master/tests/development
- Tag vault as "experimental" in v2.registry.ychad.eth
    - `registry.tagVault(vaultAddr, "https://meta.yearn.network/vaults/${vaultAddr}/vault.json")`

### Sharer contract (optional)
Sharer is a contract for distributing strategist rewards. For boarding school graduates suggested is 34% to strategist_ms and 66% to strategist.

Repo: https://github.com/Grandthrax/Sharer

- Setup rewards for your strategy by calling `sharer.addContributors`
- If you forked someone elses strategy then cut them in
- Be sure to reward people who helped you 

### Example Script:
```
# TBD Fill CMO example script to fill

```
 
## The Manual Phase
- [ ] Deposit some "want" tokens into the vault
- [ ] Do first harvest and make sure it worked correctly
    - `strategy.harvest()`
- [ ] Publish on yearn.rocks
    - Governance dev multisig ***must*** call `vault.acceptGovernance()` first
    - Talk to Facu
- [ ] Monitor harvest and tend triggers for first few days. Call harvest/tend manually

## Setting up Keep3r
- [ ] Adjust trigger variables until they are correct
    - `strategy.setProfitFactor()`
    - `strategy.setDebtThreshold()`
    - `strategy.setMaxReportDelay()`
- [ ] Add strategy to the keep3r job
    - `keep3r_manager.addStrategy(strategy, 1_500_000, 1_500_000)`
    - Tell Carlos harvest and tend gas usage. For instance 1.5m.

## Scaling Up / Moving to Endorse
- [ ] In additon to the 2 strategists, a Core Developer has to review the strategy before going into production.
- [ ] Increase limits
- [ ] Add to experimental tab on yearn.finance
- [ ] Set management fee to production level
    - `vault.setManagementFee(200)`
- [ ] Set governance to ychad.eth
- [ ] yearn governance now must accept governance and endorse
    - `strategy.acceptGovernance()` should be run by ychad.eth
    - `registry.endorseVault(strategy)` Needs ychad.eth governace accepted for this to work
    - **Order is important. Will fail if order is wrong**
- [ ] Now you are on main yearn page!

## Limits per Stage
These are the standard deposit limits per stage. They can be adjusted on a case by case basis.

| Stage | Limit |
| ---- | --- |
| Yearn.rocks / Experimental | $500K |
| Production  | $10M | 


## Revoking a strategy with normal migration
TBD

## Emergency Procedures
TBD
