# Deploying a Vault and Strategy V2

**Note**: This [repo](https://github.com/iearn-finance/chief-multisig-officer) is encouraged to create multiple scripts for governance and dev multisig execution of complex transactions.

## Deploying a new Vault

- Check latest version in `v2.registry.ychad.eth` against the planned new release vault to be sure its an updated version.
- Deploy vault for production using the new version (this should not be an experimental vault since it will be endorsed with this process).
- Set governance to `ychad.eth`:

  ```python
  vault.setGovernance(0xfeb4acf3df3cdea7399794d0869ef76a6efaff52)
  ```

- Let multisig accept governance:

  ```python
  vault.acceptGovernance()
  ```

- Let governance create a new release on `v2.registry.ychad.eth`:

  ```python
  registry.newRelease(vault)
  ```

**Note**: Last two steps may need to be done in different transactions since it sometimes can fail in practice using multisig from Gnosis.

## Deploying a new Strategy

1. Create a new issue in the strategies' [repo](https://github.com/iearn-finance/yearn-strategies/issues) using the template `Strategy Review`. **Complete all the fields**.
1. Coordinate with Core Dev strategist for getting a review on [board](https://github.com/orgs/iearn-finance/projects/5).
1. Complete peer review by at least 2 strategists.
1. Check if `want` token has a deployed vault already (>=v0.3.0) and coordinate to use that first if possible.
1. If a new vault is needed, deploy it using the registry:
   - Set Strategists multisig (`0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7`) as governance.
   - Set Core Dev multisig (`dev.ychad.eth`) as guardian.
   - Set treasury (`treasury.ychad.eth`) as the rewards address.

   ```python
   token = want
   governance = '0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7'
   guardian = '0x846e211e8ba920B353FB717631C015cf04061Cc9'
   treasury = '0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde'
   name = ''
   symbol = ''

   registry.newExperimentalVault(token, governance, guardian, treasury, name, symbol)
   ```

1. Check new vault has ABI setup on etherscan (until verification with Vyper and proxy is fixed on Etherscan).
1. Coordinate with core developer to set proper deposit limit and other settings for new vault. See the table below: [Limits per Stage](#limits-per-stage).
1. Set a deposit limit to \$50k USD converted to your `want` token. Example below is 50k DAI

   ```python
   vault.setDepositLimit(50_000 * 1e18)
   ```

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

1. Set management fee to 0:

   ```python
   vault.setManagementFee(0)
   ```

1. Set `dev.ychad.eth` as governance

   ```python
   multisig = '0x846e211e8ba920b353fb717631c015cf04061cc9'
   vault.setGovernance(multisig)
   ```

   - Governance needs to be accepted before it is in place. After you set this you will still have control over the strategy.

1. Run tests against "live" vault and strategy in mainnet-fork:

   - Harvest.
   - Profitable harvest.
   - Revoke strategy and check that funds return to the vault.
   - Increase/decrease debt + harvest, and check that the strategy is working well.
   - Migration.
   - Check that tokens in the strategy cannot be sweeped by dust collection.

   - **Example**: Hegic strat [repo](https://github.com/Macarse/yhegic/tree/master/tests/development).

1. Tag vault as "experimental" in `v2.registry.ychad.eth`
   - `registry.tagVault(vaultAddr, "https://meta.yearn.network/vaults/${vaultAddr}/vault.json")`

### Sharer contract (optional)

"Sharer" is a contract for distributing/splitting strategist rewards. For boarding school graduates suggested split is 34% to strategist multisig and 66% to strategist – [repo](https://github.com/Grandthrax/Sharer).

- Setup rewards for your strategy by calling `sharer.addContributors`.
- Include devs if you forked someone else's strategy.
- Be sure to reward people who helped you.
- You can find the sharer here: [0x2c641e14afecb16b4aa6601a40ee60c3cc792f7d](https://etherscan.io/address/0x2c641e14afecb16b4aa6601a40ee60c3cc792f7d)

## Test harvesting manually

If you need a UI to test, you can coordinate with the strategists.

1. Deposit some `want` tokens into the vault.
1. Do first `harvest` and make sure it worked correctly.

   ```python
   strategy.harvest()
   ```

1. Monitor `harvest` and `tend` triggers for first few days. Call `harvest`/`tend` manually.

## Scaling up / Moving to Endorse

In additon to the 2 strategists, a Core Developer has to review the strategy before going into production.

1. Increase deposit limit according to the table [below](#Limits-per-Stage)
1. Set management fee to production level:

   ```python
   vault.setManagementFee(200)
   ```

1. Set governance to `ychad.eth`:

   ```python
   vault.setGovernance(0xfeb4acf3df3cdea7399794d0869ef76a6efaff52)
   ```

Yearn governance now must accept governance and endorse the vault:
  **Note**: Order is important. Will fail if order is wrong.

### Endorsing a vault from latest release

This must be done from the multisig

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

1. Now you are on the main site!

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

### Addresses

| Identity               | ENS                   | Address                                    |
| ---------------------- | --------------------- |------------------------------------------- |
| V2 Registry            | v2.registry.ychad.eth | 0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804 |
| Yearn multisig (daddy) | ychad.eth             | 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52 |
| Strategist multisig    |                       | 0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7 |
| Core Dev multisig      | dev.ychad.eth         | 0x846e211e8ba920B353FB717631C015cf04061Cc9 |
| Treasury               | treasury.ychad.eth    | 0xfeb4acf3df3cdea7399794d0869ef76a6efaff52 |
