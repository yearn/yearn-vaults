# Operations procedures

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
