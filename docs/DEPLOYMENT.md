# Deploying a Vault and Strategy V2

**Note**: This [repo](https://github.com/iearn-finance/chief-multisig-officer) is encouraged to create multiple scripts for governance and dev multisig execution of complex transactions.

## Requirements

Make sure you have the brownie environment setup before trying to deploy a vault. Check out the [Readme MD](https://github.com/yearn/yearn-vaults/blob/master/README.md) for instructions.

The below instructions show some python commands that assume you are using the brownie console or a brownie script setup is in place.

## Deploying a new Experimental Vault

1. Clone this repo and run `brownie run scripts/deploy.py --network <network-to-deploy-vault>`
1. Choose the brownie account for deploying your vault. This account needs to have balance to pay for the deploy transaction.
1. Confirm the script is using the latest version of registry `v2.registry.ychad.eth` against the planned new release vault to be sure its an updated version. (Can validate on Etherscan for latest address)
1. Select the version of vault to deploy or press enter to use latest release.
1. Enter `Y` when prompt to deploy Proxy Vault
1. Enter the checksummed address of the ERC20 token the vault will use. 
1. Enter the vault Parameters (Below are some suggested values):
   - Set your address or an address you control as governance.
   - Set Treasury (`treasury.ychad.eth`) as the rewards address.
   - Set Core Dev multisig (`dev.ychad.eth`) as guardian.
   - Set Strategist multisig (`brain.ychad.eth`) as management.
   - Set description and symbol for vault or use suggested as default (can be changed on chain later)
1. Confirm the Parameters are set correctly and press `y`and ENTER to deploy vault. 
   
1. Check new vault has ABI setup on Etherscan (Some vault versions from older releases may have verification issues with Vyper and proxy detection on Etherscan, consider using latest releases >0.3.5 to ensure verification works).

1. Set up the vault with correct deposit limit:

   ```python
   vault.setDepositLimit(limit)
   ```
1. Set management fee to 0:

   ```python
   vault.setManagementFee(0)
   ```

1. (Optional) Set governance to ychad.eth (`0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52`) if vault is planned to be endorsed soon:
  - Note you can still make changes to the vault after setting governance up until governance is accepted

   ```python
   vault.setGovernance(ychad.eth)
   ```


## Deploying a new Strategy

1. Create a new issue in the strategies' [repo](https://github.com/iearn-finance/yearn-strategies/issues) using the template `Strategy Review`. **Complete all the fields**.
1. If the strategy is targeting a new protocol/new chain, not currently approved by yearn (used in production), a due diligence and path to production plan documents may also be required for the strategy to be considered for endorsing. [PATH TO PROD](PATH_TO_PROD.md)
Examples [SNX](https://hackmd.io/0w1RZh7DSc27A9EyzlHbJQ?view), [VESPER](https://hackmd.io/@Ap_76vwNTg-vxJxbiaLMMQ/SkXEzic7O) 
1. Coordinate with Core Dev strategist for getting a review on [board](https://github.com/orgs/iearn-finance/projects/5).
1. Complete peer review by at least 2 strategists.
1. Check if `want` token has a deployed vault already (>=v0.3.0) and coordinate to use that first if possible.
1. Coordinate with core developer to set proper deposit limit and other settings for new vault. See the table below: [Limits per Stage](#limits-per-stage).
1. Deploy strategy and upload code to Etherscan for verification.
1. Tag GitHub review issue with deployed version and add mainnet address(es) to the [board](https://github.com/orgs/iearn-finance/projects/5).

## Make the Vault and Strategy work together

1. Add strategy to vault (for vault code v0.3.3+):

   ```python
   strategy = ''                     # Your strategy address
   debt_ratio = 9800                 # 98%
   minDebtPerHarvest = 0             # Lower limit on debt add
   maxDebtPerHarvest = 2 ** 256 - 1  # Upper limit on debt add
   performance_fee = 1000            # Strategist perf fee: 10%

   vault.addStrategy(
     strategy, 
     debt_ratio, 
     minDebtPerHarvest,
     maxDebtPerHarvest,
     performance_fee
   )
   ```

   - `debt_ratio` should be `9800` if first strategy on vault.
   - `rate_limit` is `0` unless there is reason for it to be different.

1. Set keeper:

   ```python
   strategy.setKeeper(keep3r_manager)
   ```

   - `keep3r_manager` = `0x736D7e3c5a6CB2CE3B764300140ABF476F6CFCCF`

1. Set rewards:

   ```python
   strategy.setRewards(address)
   ```

   - Read [below](<#Sharer-contract-(optional)>) if you want to use the sharer contract.

1. Run tests against "live" vault and strategy in mainnet-fork:

   - Harvest.
   - Profitable harvest.
   - Revoke strategy and check that funds return to the vault.
   - Increase/decrease debt + harvest, and check that the strategy is working well.
   - Migration.
   - Check that tokens in the strategy cannot be sweeped by dust collection.

   - **Example**: Hegic strat [repo](https://github.com/Macarse/yhegic/tree/master/tests/development).

## Test harvesting manually

If you need a UI to test, you can coordinate with the strategists.

1. Deposit some `want` tokens into the vault.
1. Do first `harvest` and make sure it worked correctly.

   ```python
   strategy.harvest()
   ```

1. Monitor `harvest` and `tend` triggers for first few days. Call `harvest`/`tend` manually.

## Scaling up / Moving to Endorse

In addition to the 2 strategists, a Core Developer has to review the strategy before going into production.

1. Increase deposit limit according to the table [below](#Limits-per-Stage)
1. Set management fee to production level:

   ```python
   vault.setManagementFee(200)
   ```

1. Set parameters for vault correctly before endorse:
   - Set Governance to (`ychad.eth`) 
   - Set Treasury (`treasury.ychad.eth`) as the rewards address.
   - Set Core Dev multisig (`dev.ychad.eth`) as guardian.
   - Set Strategist multisig (`brain.ychad.eth`) as management.
   - Set description and symbol for vault or use suggested as default (can be changed on chain later)

1. Yearn governance now must accept governance and endorse the vault:

```python
strategy.acceptGovernance()
registry.endorseVault(vault)
```

### Endorsing a vault from a previous release

1. Check for latest release number in the registry contract
1. Check the apiVersion of the vault you want to endorse to identify target release
1. Calculate the releaseDelta from your target release. (see registry endorseVault param details)
   E.g: latestRelease = 0.3.3 and numReleases = 5. New vault apiVersion is 0.3.2
   `releaseDelta = numReleases - 1 - releaseTarget`
1. Confirm using `registry.releases(uint256)` that your `targetRelease` has the same apiVersion as your vault.

   ```python
   releaseTarget = 3 # e.g vault api version 0.3.2
   releaseDelta = registry.numReleases() - 1 - releaseTarget # (5-1-3) = 1
   strategy.acceptGovernance() # from ychad.eth
   registry.endorseVault(vault, releaseDelta) # from ychad.eth.
   ```

## Setting up Keep3r

1. Adjust trigger variables until they are correct:

   ```python
   strategy.setProfitFactor()
   strategy.setDebtThreshold()
   strategy.setMaxReportDelay()
   ```

1. Set strategy's Keep3r role to v2-keeper-contract

   ```python
   strategy.setKeeper(0x736D7e3c5a6CB2CE3B764300140ABF476F6CFCCF)
   ```

1. Create an add-strategy PR in Keep3r [repo](https://github.com/iearn-finance/yearn-keeper) (TBD)

## References

### Limits per Stage

These are the standard deposit limits per stage. They can be adjusted on a case by case basis.

| Stage        | Limit  |
| ------------ | ------ |
| Experimental | \$500K |
| Production   | \$10M  |

### Sharer contract

"Sharer" is a contract for distributing/splitting strategist rewards. For boarding school graduates suggested split is 34% to strategist multisig and 66% to strategist – [Sharer Contract](https://github.com/Grandthrax/Sharer).

- Setup rewards for your strategy by calling `sharer.addContributors`.
- Include devs if you forked someone else's strategy.
- Be sure to reward people who helped you.
- You can find the sharer here: [0x2c641e14afecb16b4aa6601a40ee60c3cc792f7d](https://etherscan.io/address/0x2c641e14afecb16b4aa6601a40ee60c3cc792f7d)

### Addresses

| Identity               | ENS                   | Address                                    |
| ---------------------- | --------------------- |------------------------------------------- |
| V2 Registry            | v2.registry.ychad.eth | 0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804 |
| Yearn multisig (daddy) | ychad.eth             | 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52 |
| Strategist multisig    |   brain.ychad.eth                    | 0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7 |
| Core Dev multisig      | dev.ychad.eth         | 0x846e211e8ba920B353FB717631C015cf04061Cc9 |
| Treasury               | treasury.ychad.eth    | 0xfeb4acf3df3cdea7399794d0869ef76a6efaff52 |
