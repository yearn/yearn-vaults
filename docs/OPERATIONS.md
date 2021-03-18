# Deploy a Strategy / Vault for V2

**Note**: This [repo](https://github.com/iearn-finance/chief-multisig-officer) is encouraged to create multiple scripts for governance and dev multisig execution of complex transactions.

**IMPORTANT**: you should **NOT** create a new release with a test vault, it will be endorsed as a production.

## Process for new vault release

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

## Before deployment

- Create a new issue in the strategies' [repo](https://github.com/iearn-finance/yearn-strategies/issues) using the template `Strategy Review`. **Complete all the fields**.
- Coordinate with Core Dev strategist for getting a review on [board](https://github.com/orgs/iearn-finance/projects/5).
- Complete peer review by at least 2 strategists.
- Check if `want` token has a deployed vault already (>=v0.3.0) and coordinate to use that first if possible.
- If a new vault is needed, deploy it using the registry:
  - Set strategists multisig (`0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7`) as governance.
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

- Check new vault has ABI setup on etherscan (until verification with Vyper and proxy is fixed on Etherscan).
- Coordinate with core developer to set proper deposit limit and other settings for new vault. See the table below: [Limits per Stage](#limits-per-stage).
- Set a deposit limit to \$50k USD converted to your `want` token. Example below is 50k DAI

  ```python
  vault.setDepositLimit(50_000 * 1e18)
  ```

- Deploy strategy and upload code to Etherscan for verification.
- Tag GitHub review issue with deployed version and add mainnet address(es) to the [board](https://github.com/orgs/iearn-finance/projects/5).

## After deployment

- Add strategy to vault:

  ```python
  strategy = ''                     # Strategy address
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

- Set keeper:

  ```python
  strategy.setKeeper(keep3r_manager)
  ```

  - `keep3r_manager` = `0x13dAda6157Fee283723c0254F43FF1FdADe4EEd6`

- Set rewards:

  ```python
  strategy.setRewards(address)
  ```

  - Read [below](<#Sharer-contract-(optional)>) if you want to use the sharer contract.

- Set management fee to 0:

  ```python
  vault.setManagementFee(0)
  ```

- Set `dev.ychad.eth` as governance

  ```python
  multisig = '0x846e211e8ba920b353fb717631c015cf04061cc9'
  vault.setGovernance(multisig)
  ```

  - Governance needs to be accepted before it is in place. After you set this you will still have control over the strategy.

- Run tests against "live" vault and strategy in mainnet-fork:

  - Harvest.
  - Profitable harvest.
  - Revoke strategy and check that funds return to the vault.
  - Increase/decrease debt + harvest, and check that the strategy is working well.
  - Migration.
  - Check that tokens in the strategy cannot be sweeped by dust collection.

  Example: Hegic strat [repo](https://github.com/Macarse/yhegic/tree/master/tests/development).

- Tag vault as "experimental" in `v2.registry.ychad.eth`
  - `registry.tagVault(vaultAddr, "https://meta.yearn.network/vaults/${vaultAddr}/vault.json")`

### Sharer contract (optional)

"Sharer" is a contract for distributing/splitting strategist rewards. For boarding school graduates suggested split is 34% to strategist multisig and 66% to strategist – [repo](https://github.com/Grandthrax/Sharer).

- Setup rewards for your strategy by calling `sharer.addContributors`.
- Include devs if you forked someone else's strategy.
- Be sure to reward people who helped you.

### Example Script

```python
# TBD Fill CMO example script to fill
```

## The Manual Phase

- Deposit some `want` tokens into the vault.
- Do first `harvest` and make sure it worked correctly.

  ```python
  strategy.harvest()
  ```

- If you need a UI to test, you can coordinate with the strategists.

- Monitor `harvest` and `tend` triggers for first few days. Call `harvest`/`tend` manually.

## Scaling up / Moving to Endorse

- In additon to the 2 strategists, a Core Developer has to review the strategy before going into production.
- Increase limits.
- Add to experimental tab on yearn.finance.
- Set management fee to production level:

  ```python
  vault.setManagementFee(200)
  ```

- Set governance to `ychad.eth`:

  ```python
  vault.setGovernance(0xfeb4acf3df3cdea7399794d0869ef76a6efaff52)
  ```

- Yearn governance now must accept governance and endorse the vault:

  ```python
  strategy.acceptGovernance() # from ychad.eth
  registry.endorseVault(vault) # from ychad.eth
  ```

  **Note**: Order is important. Will fail if order is wrong.

- Now you are on main yearn page!

## Setting up Keep3r

- Adjust trigger variables until they are correct:
  - `strategy.setProfitFactor()`
  - `strategy.setDebtThreshold()`
  - `strategy.setMaxReportDelay()`
- Set strategy's Keep3r role to v2-keeper-contract (TBD)
- Create an add-strategy PR in Keep3r [repo](https://github.com/iearn-finance/yearn-keeper) (TBD)

## Limits per Stage

These are the standard deposit limits per stage. They can be adjusted on a case by case basis.

| Stage                      | Limit  |
| -------------------------- | ------ |
| Experimental               | \$500K |
| Production                 | \$10M  |

## Revoking a strategy with normal migration

Let's say we found a problem in one of the strategies and we want to return all funds. There are two ways of doing it.

The scripts below use the HEGIC vault as an example.

### From the vault

```python
# Grab the gov account
gov = accounts.at(vault.governance(), force=True)

# The cream strategy is the first in the withdrawal queue
s1 = Contract(vault.withdrawalQueue(0))

# Revoke msg should be sent from gov or guardian
vault.revokeStrategy(s1, {"from": gov})
```

After running the command you will notice:

```python
vault.strategies(s1).dict()['debtRatio'] == 0
```

Last step is running a `harvest` to return funds to vault:

```python
s1.harvest({"from": gov})
>>> hegic.balanceOf(s1)
0
>>> hegic.balanceOf(vault)/1e18
291731.2666932462
```

### From the strategy

From the strategy itself we can turn on emergency mode.
To do it we need to run:

```python
# Grab the strategist account
strategist = accounts.at(s1.strategist(), force=True)

# Turn on the emergency exit
s1.setEmergencyExit({'from': strategist})

# Harvest to move funds to the vault
s1.harvest({'from': strategist})
```

We should also see the strategy's `debtRatio` going to `0` and funds returning to the vault.

## Emergency Procedures

We can also shutdown the vault to return assets as soon as possible. To do that we will need a guardian or governance account:

```python
# Sound the alarm
vault.setEmergencyShutdown(true, {'from': gov})

# Harvest all strategies
s1.harvest({'from': gov})
s2.harvest({'from': gov})
s3.harvest({'from': gov})

# Check all the tokens are back in the vault
>>> hegic.balanceOf(vault) == vault.totalAssets()
True
```

You will notice that this procedure doesn't change the debt ratio:

```python
>>> vault.strategies(s1).dict()['debtRatio']
1600
```

It drops the credit to `0`:

```python
>>> vault.creditAvailable(s1)
0
```

## References

### Addresses
| Identity      | ENS | Address      |
| ----------- | ----------- |----------- |
| V2 Registry      | v2.registry.ychad.eth |    0x50c1a2eA0a861A967D9d0FFE2AE4012c2E053804 |
| Yearn multisig (daddy)      | ychad.eth |    0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52 |
| Strategist multisig      |        | 0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7       |
| Core Dev multisig   | dev.ychad.eth        | 0x846e211e8ba920B353FB717631C015cf04061Cc9       |
| Treasury   | treasury.ychad.eth        | 0xfeb4acf3df3cdea7399794d0869ef76a6efaff52       |