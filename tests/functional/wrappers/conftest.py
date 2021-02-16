import pytest


@pytest.fixture
def ytoken(token, gov, yToken):
    # Official Yearn Wrapper
    yield gov.deploy(yToken, token)


@pytest.fixture
def affiliate(management):
    yield management  # NOTE: Not necessary for these tests


@pytest.fixture
def affiliate_token(token, affiliate, AffiliateToken):
    # Affliate Wrapper
    yield affiliate.deploy(
        AffiliateToken, token, f"Affiliate {token.symbol()}", f"af{token.symbol()}"
    )


@pytest.fixture
def weth(web3, Token, gov):
    # WETH9 deployment txn
    txn = web3._mainnet.eth.getTransaction(
        "0xb95343413e459a0f97461812111254163ae53467855c0d73e0f1e7c5b8442fa3"
    )
    txn = gov.transfer(data=txn["input"])
    yield Token.at(txn.contract_address)
