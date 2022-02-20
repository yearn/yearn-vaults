import brownie

from eth_account import Account


def test_config(gov, token, vault, registry, ytoken):
    assert ytoken.token() == token
    assert ytoken.name() == "Yearn " + token.name()
    assert ytoken.symbol() == "y" + token.symbol()
    assert ytoken.decimals() == token.decimals()

    # No vault added to the registry yet, so these methods should fail
    assert registry.numVaults(token) == 0

    # This won't revert though, there's no Vaults yet
    assert ytoken.allVaults() == []

    # Now they work when we have a Vault
    registry.newRelease(vault, {"from": gov})
    registry.endorseVault(vault, {"from": gov})
    assert ytoken.bestVault() == vault
    assert ytoken.allVaults() == [vault]


def test_setRegistry(rando, gov, ytoken, new_registry):
    # Only yGov can call this method
    with brownie.reverts():
        ytoken.setRegistry(new_registry, {"from": rando})

    # Cannot set to an invalid registry
    with brownie.reverts():
        ytoken.setRegistry(rando, {"from": gov})

    # yGov must be the gov on the new registry too
    new_registry.setGovernance(rando, {"from": gov})
    new_registry.acceptGovernance({"from": rando})
    with brownie.reverts():
        ytoken.setRegistry(new_registry, {"from": gov})
    new_registry.setGovernance(gov, {"from": rando})
    new_registry.acceptGovernance({"from": gov})

    ytoken.setRegistry(new_registry, {"from": gov})


def test_deposit(token, registry, vault, ytoken, gov, rando):
    registry.newRelease(vault, {"from": gov})
    registry.endorseVault(vault, {"from": gov})
    token.transfer(rando, 10000, {"from": gov})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 0

    # NOTE: Must approve ytoken to deposit
    token.approve(ytoken, 10000, {"from": rando})
    ytoken.deposit(10000, {"from": rando})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 10000


def test_transfer(token, registry, vault, ytoken, gov, rando, affiliate):
    registry.newRelease(vault, {"from": gov})
    registry.endorseVault(vault, {"from": gov})
    token.transfer(rando, 10000, {"from": gov})
    token.approve(ytoken, 10000, {"from": rando})
    ytoken.deposit(10000, {"from": rando})

    # NOTE: Must approve ytoken to withdraw and send
    vault.approve(ytoken, 10000, {"from": rando})
    # NOTE: Just using `affiliate` as a random address
    ytoken.transfer(affiliate, 10000, {"from": rando})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 0
    assert token.balanceOf(rando) == 0
    assert token.balanceOf(affiliate) == 10000


def test_withdraw(token, registry, vault, ytoken, gov, rando):
    registry.newRelease(vault, {"from": gov})
    registry.endorseVault(vault, {"from": gov})
    token.transfer(rando, 10000, {"from": gov})
    token.approve(ytoken, 10000, {"from": rando})
    ytoken.deposit(10000, {"from": rando})

    # NOTE: Must approve ytoken to withdraw
    vault.approve(ytoken, 10000, {"from": rando})
    ytoken.withdraw(10000, {"from": rando})
    assert ytoken.balanceOf(rando) == vault.balanceOf(rando) == 0
    assert token.balanceOf(rando) == 10000


def test_migrate(token, registry, create_vault, sign_vault_permit, ytoken, gov):
    rando = Account.create()
    token.transfer(rando.address, 10000, {"from": gov})
    token.approve(ytoken, 10000, {"from": rando.address})

    vault1 = create_vault(version="1.0.0", token=token)
    registry.newRelease(vault1, {"from": gov})
    registry.endorseVault(vault1, {"from": gov})

    assert registry.latestVault(token) == vault1

    ytoken.deposit(5000, {"from": rando.address})
    assert vault1.balanceOf(rando.address) == 5000

    vault2 = create_vault(version="2.0.0", token=token)
    registry.newRelease(vault2, {"from": gov})
    registry.endorseVault(vault2, {"from": gov})
    assert registry.latestVault(token) == vault2

    ytoken.deposit(5000, {"from": rando.address})
    assert vault1.balanceOf(rando.address) == 5000
    assert vault2.balanceOf(rando.address) == 5000

    sig1 = sign_vault_permit(vault1, rando, ytoken.address)
    sig2 = sign_vault_permit(vault2, rando, ytoken.address)
    ytoken.permitAll([vault1, vault2], [sig1, sig2], {"from": rando.address})
    assert vault1.allowance(rando.address, ytoken) == 2 ** 256 - 1
    assert vault2.allowance(rando.address, ytoken) == 2 ** 256 - 1

    ytoken.migrate({"from": rando.address})
    assert vault1.balanceOf(rando.address) == 0
    assert vault2.balanceOf(rando.address) == 10000

    sig1 = sign_vault_permit(vault1, rando, ytoken.address, allowance=0)
    sig2 = sign_vault_permit(vault2, rando, ytoken.address, allowance=0)
    ytoken.revokeAll([vault1, vault2], [sig1, sig2], {"from": rando.address})
    assert vault1.allowance(rando.address, ytoken) == 0
    assert vault2.allowance(rando.address, ytoken) == 0


def test_yweth_wrapper(gov, rando, registry, create_vault, weth, yWETH):
    vault1 = create_vault(version="1.0.0", token=weth)
    registry.newRelease(vault1, {"from": gov})
    registry.endorseVault(vault1, {"from": gov})
    assert registry.latestVault(weth) == vault1
    yweth = yWETH.deploy(weth, registry, {"from": gov})
    assert yweth.token() == weth

    # Deposits from ETH work just fine
    amount = rando.balance()
    yweth.depositETH({"from": rando, "value": amount})
    assert vault1.balanceOf(rando) == amount

    vault2 = create_vault(version="2.0.0", token=weth)
    registry.newRelease(vault2, {"from": gov})
    registry.endorseVault(vault2, {"from": gov})
    assert registry.latestVault(weth) == vault2

    # Migrations work just fine
    assert vault1.balanceOf(rando) == amount
    assert vault2.balanceOf(rando) == 0
    vault1.approve(yweth, amount, {"from": rando})
    yweth.migrate({"from": rando})
    assert vault1.balanceOf(rando) == 0
    assert vault2.balanceOf(rando) == amount

    # Withdrawing to ETH works just fine
    vault2.approve(yweth, amount, {"from": rando})
    yweth.withdrawETH(amount, {"from": rando})
    assert vault1.balanceOf(rando) == 0
    assert vault2.balanceOf(rando) == 0
    assert rando.balance() == amount

    # Also check straight ether transfers work
    rando.transfer(yweth, amount)
    assert vault2.balanceOf(rando) == amount
