import brownie
from brownie import ZERO_ADDRESS

def test_vault_pause_permissions(gov, vault, rando, guardian):
    # Rando Cannot Pause
    with brownie.reverts():
        vault.pause({"from": rando})
    
    # Guardian can pause
    vault.pause({"from": guardian})

    assert vault.paused() == True

    # Rando Cannot Unpause
    with brownie.reverts():
        vault.unpause({"from": rando})

    # Guardian Cannot Unpause
    with brownie.reverts():
        vault.unpause({"from": guardian})

    # Governance can Unpause
    vault.unpause({"from": gov})

    assert vault.paused() == False

    # Governance can pause
    vault.pause({"from": gov})

    assert vault.paused() == True

def test_vault_pause_action_block(gov, vault, rando):
    vault.pause({"from": gov})

    ## You cannot deposit
    with brownie.reverts("dev: paused"):
      vault.deposit(1, {"from": rando})

    ## You cannot withdraw
    with brownie.reverts("dev: paused"):
      vault.withdraw(1, {"from": rando})
    
    ## You cannot approve
    with brownie.reverts("dev: paused"):
      vault.approve(rando, 1, {"from": rando})

    ## You cannot transfer
    with brownie.reverts("dev: paused"):
      vault.transfer(rando, 1, {"from": rando})

    ## You cannot increaseAllowance
    with brownie.reverts("dev: paused"):
      vault.increaseAllowance(rando, 1, {"from": rando})

    ## You cannot decreaseAllowance
    with brownie.reverts("dev: paused"):
      vault.decreaseAllowance(rando, 1, {"from": rando})

def test_approve_contract_permissions(gov, guardian, rando, vault):
  ## Rando cannot approve contract
  with brownie.reverts("dev: only governance"):
    vault.approveContractAccess(ZERO_ADDRESS, {"from": rando})
  ## Guardian cannot approve contract
  with brownie.reverts("dev: only governance"):
    vault.approveContractAccess(ZERO_ADDRESS, {"from": guardian})
  
  ## Governance CAN approve contract
  vault.approveContractAccess(ZERO_ADDRESS, {"from": gov})
  assert vault.approved(ZERO_ADDRESS) == True

    ## Rando cannot revoke contract
  with brownie.reverts("dev: only governance"):
    vault.revokeContractAccess(ZERO_ADDRESS, {"from": rando})
  ## Guardian cannot revoke contract
  with brownie.reverts("dev: only governance"):
    vault.revokeContractAccess(ZERO_ADDRESS, {"from": guardian})

  ## Governance CAN revoke contract
  vault.revokeContractAccess(ZERO_ADDRESS, {"from": gov})
  assert vault.approved(ZERO_ADDRESS) == False


def test_vault_defend_add(gov, vault, deposit_contract):
  ## NOTE: Can't get error message
  with brownie.reverts():
    deposit_contract.deposit(1, {"from": gov})

  ## If I approve it should work
  vault.approveContractAccess(deposit_contract, {"from": gov})
  deposit_contract.deposit(1, {"from": gov})
  assert vault.balanceOf(deposit_contract) > 0

  ## If I revoke it also needs to revert
  vault.revokeContractAccess(deposit_contract, {"from": gov})

  ## NOTE: Can't get error message
  with brownie.reverts():
    deposit_contract.deposit(1, {"from": gov})


def test_flash_loan_lock_for_block(gov, vault, flashloan_contract):
  ## Can't work if not approved
  ## NOTE: Can't get error message
  with brownie.reverts():
    flashloan_contract.flashLoan(1, {"from": gov})
  
  ## If I approve it will revert due to block for lock
  vault.approveContractAccess(flashloan_contract, {"from": gov})
  ## NOTE: Can't get error message
  with brownie.reverts():
    flashloan_contract.flashLoan(1, {"from": gov})
