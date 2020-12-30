import pytest
import brownie


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Overriding the one in conftest because it has values already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, token.symbol() + " yVault", "yv" + token.symbol(), gov
    )
    yield vault


@pytest.fixture
def guest_list(gov, TestGuestList):
    yield gov.deploy(TestGuestList)


def test_deposit_with_zero_funds(vault, token, rando):
    assert token.balanceOf(rando) == 0
    token.approve(vault, 2 ** 256 - 1, {"from": rando})
    with brownie.reverts():
        vault.deposit({"from": rando})


def test_deposit_with_wrong_amount(vault, token, gov):
    balance = token.balanceOf(gov) + 1
    token.approve(vault, 2 ** 256 - 1, {"from": gov})
    with brownie.reverts():
        vault.deposit(balance, {"from": gov})


def test_deposit_with_guest_list(vault, guest_list, token, gov, rando, history):
    # Make sure we're attempting to deposit something
    token.transfer(rando, token.balanceOf(gov) // 2, {"from": gov})
    balance = token.balanceOf(rando)
    token.approve(vault, balance, {"from": rando})

    # Note - don't need to call guest_list.setGuests, since nobody's invited by
    # default.
    # gov is our bouncer
    vault.setGuestList(guest_list, {"from": gov})

    # Ensure rando's not permitted to deposit
    with brownie.reverts():
        vault.deposit(balance, {"from": rando})

    # Ensure authorized was called and that the deposit didn't revert for a
    # different reason.
    assert history[-1].subcalls[-1]["function"] == "authorized(address,uint256)"
    assert history[-1].subcalls[-1]["return_value"][0] == False

    # Allow rando into the party
    guests = [rando]
    invited = [True]
    guest_list.setGuests(guests, invited, {"from": gov})

    # Deposit balance
    vault.deposit(balance, {"from": rando})

    # Ensure the vault now has all rando's tokens
    assert token.balanceOf(rando) == 0
    assert vault.balanceOf(rando) == balance


def test_deposit_all_and_withdraw_all(gov, vault, token):
    balance = token.balanceOf(gov)
    token.approve(vault, token.balanceOf(gov), {"from": gov})

    # Take up the rest of the deposit limit only
    vault.setDepositLimit(token.balanceOf(gov) // 2, {"from": gov})
    vault.deposit({"from": gov})
    # vault has tokens
    assert token.balanceOf(vault) == balance // 2
    # sender has vault shares
    assert vault.balanceOf(gov) == balance // 2

    # When deposit limit is lifted, deposit everything
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.deposit({"from": gov})
    # vault has tokens
    assert token.balanceOf(vault) == balance
    # sender has vault shares
    assert vault.balanceOf(gov) == balance

    vault.withdraw({"from": gov})
    # vault no longer has tokens
    assert token.balanceOf(vault) == 0
    # sender no longer has shares
    assert vault.balanceOf(gov) == 0
    # sender has tokens
    assert token.balanceOf(gov) == balance


def test_deposit_withdraw(gov, vault, token):
    balance = token.balanceOf(gov)
    token.approve(vault, balance, {"from": gov})
    vault.deposit(balance // 2, {"from": gov})

    assert token.balanceOf(vault) == balance // 2
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    # Do it twice to test behavior when it has shares
    vault.deposit({"from": gov})

    assert vault.totalSupply() == token.balanceOf(vault) == balance
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    vault.withdraw(vault.balanceOf(gov) // 2, {"from": gov})

    assert token.balanceOf(vault) == balance // 2
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    # Can't withdraw more shares than we have
    with brownie.reverts():
        vault.withdraw(2 * vault.balanceOf(gov), {"from": gov})

    vault.withdraw({"from": gov})
    assert vault.totalSupply() == token.balanceOf(vault) == 0
    assert vault.totalDebt() == 0
    assert token.balanceOf(gov) == balance


def test_deposit_limit(gov, token, vault):
    token.approve(vault, 2 ** 256 - 1, {"from": gov})

    vault.setDepositLimit(0, {"from": gov})

    # Deposits are locked out
    with brownie.reverts():
        vault.deposit({"from": gov})

    balance = token.balanceOf(gov)
    vault.setDepositLimit(balance // 2, {"from": gov})

    # Can deposit less than limit
    vault.deposit(balance // 3, {"from": gov})
    assert vault.balanceOf(gov) == balance // 3

    # With the integer arg, it must be at or below the limit
    with brownie.reverts():
        vault.deposit(token.balanceOf(gov), {"from": gov})

    # Without the integer arg, it takes up to whatever's left
    vault.deposit({"from": gov})
    assert vault.balanceOf(gov) == balance // 2

    # Deposits are locked out
    with brownie.reverts():
        vault.deposit({"from": gov})

    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})

    # Now it will take the rest
    vault.deposit({"from": gov})


def test_delegated_deposit_withdraw(accounts, token, vault):
    a, b, c, d, e = accounts[0:5]

    # Store original amount of tokens so we can assert
    # Number of tokens will be equal to number of shares since no returns are generated
    originalTokenAmount = token.balanceOf(a)

    # Make sure we have tokens to play with
    assert originalTokenAmount > 0

    # 1. Deposit from a and send shares to b
    token.approve(vault, token.balanceOf(a), {"from": a})
    vault.deposit(token.balanceOf(a), b, {"from": a})

    # a no longer has any tokens
    assert token.balanceOf(a) == 0
    # a does not have any vault shares
    assert vault.balanceOf(a) == 0
    # b has been issued the vault shares
    assert vault.balanceOf(b) == originalTokenAmount

    # 2. Withdraw from b to c
    vault.withdraw(vault.balanceOf(b), c, {"from": b})

    # b no longer has any shares
    assert vault.balanceOf(b) == 0
    # b did not receive the tokens
    assert token.balanceOf(b) == 0
    # c has the tokens
    assert token.balanceOf(c) == originalTokenAmount

    # 3. Deposit all from c and send shares to d
    token.approve(vault, token.balanceOf(c), {"from": c})
    vault.deposit(token.balanceOf(c), d, {"from": c})

    # c no longer has the tokens
    assert token.balanceOf(c) == 0
    # c does not have any vault shares
    assert vault.balanceOf(c) == 0
    # d has been issued the vault shares
    assert vault.balanceOf(d) == originalTokenAmount

    # 4. Withdraw from d to e
    vault.withdraw(vault.balanceOf(d), e, {"from": d})

    # d no longer has any shares
    assert vault.balanceOf(d) == 0
    # d did not receive the tokens
    assert token.balanceOf(d) == 0
    # e has the tokens
    assert token.balanceOf(e) == originalTokenAmount


def test_emergencyShutdown(gov, vault, token):
    balance = token.balanceOf(gov)
    token.approve(vault, balance, {"from": gov})
    vault.deposit(balance // 2, {"from": gov})

    assert token.balanceOf(vault) == balance // 2
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price

    vault.setEmergencyShutdown(True, {"from": gov})

    # Deposits are locked out
    with brownie.reverts():
        vault.deposit({"from": gov})

    # But withdrawals are fine
    vault.withdraw(vault.balanceOf(gov), {"from": gov})
    assert token.balanceOf(vault) == 0
    assert token.balanceOf(gov) == balance


def test_transfer(accounts, token, vault):
    a, b = accounts[0:2]
    token.approve(vault, token.balanceOf(a), {"from": a})
    vault.deposit({"from": a})

    assert vault.balanceOf(a) == token.balanceOf(vault)
    assert vault.balanceOf(b) == 0

    # Can't send your balance to the Vault
    with brownie.reverts():
        vault.transfer(vault, vault.balanceOf(a), {"from": a})

    # Can't send your balance to the zero address
    with brownie.reverts():
        vault.transfer(
            "0x0000000000000000000000000000000000000000",
            vault.balanceOf(a),
            {"from": a},
        )

    vault.transfer(b, vault.balanceOf(a), {"from": a})

    assert vault.balanceOf(a) == 0
    assert vault.balanceOf(b) == token.balanceOf(vault)


def test_transferFrom(accounts, token, vault):
    a, b, c = accounts[0:3]
    token.approve(vault, token.balanceOf(a), {"from": a})
    vault.deposit({"from": a})

    # Unapproved can't send
    with brownie.reverts():
        vault.transferFrom(a, b, vault.balanceOf(a) // 2, {"from": c})

    vault.approve(c, vault.balanceOf(a) // 2, {"from": a})
    assert vault.allowance(a, c) == vault.balanceOf(a) // 2

    vault.increaseAllowance(c, vault.balanceOf(a) // 2, {"from": a})
    assert vault.allowance(a, c) == vault.balanceOf(a)

    vault.decreaseAllowance(c, vault.balanceOf(a) // 2, {"from": a})
    assert vault.allowance(a, c) == vault.balanceOf(a) // 2

    # Can't send more than what is approved
    with brownie.reverts():
        vault.transferFrom(a, b, vault.balanceOf(a), {"from": c})

    assert vault.balanceOf(a) == token.balanceOf(vault)
    assert vault.balanceOf(b) == 0

    vault.transferFrom(a, b, vault.balanceOf(a) // 2, {"from": c})

    assert vault.balanceOf(a) == token.balanceOf(vault) // 2
    assert vault.balanceOf(b) == token.balanceOf(vault) // 2

    # If approval is unlimited, little bit of a gas savings
    vault.approve(c, 2 ** 256 - 1, {"from": a})
    vault.transferFrom(a, b, vault.balanceOf(a), {"from": c})

    assert vault.balanceOf(a) == 0
    assert vault.balanceOf(b) == token.balanceOf(vault)
