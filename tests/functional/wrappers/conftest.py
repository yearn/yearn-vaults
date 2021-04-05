from pathlib import Path

import pytest

# 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 on Mainnet
WETH_BYTECODE = (Path(__file__).parent / "weth.bytecode").read_text().strip()


@pytest.fixture
def weth(Token, gov):
    # WETH9 deployment bytecode
    txn = gov.transfer(data=WETH_BYTECODE)
    yield Token.at(txn.contract_address)


@pytest.fixture
def ytoken(token, gov, registry, yToken):
    # Official Yearn Wrapper
    yield gov.deploy(yToken, token, registry)


@pytest.fixture
def affiliate(management):
    yield management  # NOTE: Not necessary for these tests


@pytest.fixture
def affiliate_token(token, affiliate, registry, AffiliateToken):
    # Affliate Wrapper
    yield affiliate.deploy(
        AffiliateToken,
        token,
        registry,
        f"Affiliate {token.symbol()}",
        f"af{token.symbol()}",
    )


@pytest.fixture
def new_registry(Registry, gov):
    yield gov.deploy(Registry)
