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
