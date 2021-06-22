import pytest
import brownie


def test_registry_deployment(gov, registry):
    assert registry.governance() == gov
    assert registry.numReleases() == 0
