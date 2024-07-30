# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
import pytest
from ops.testing import Harness

from charm import HAProxyCharm


@pytest.fixture(scope="function", name="harness")
def harness_fixture():
    """Enable ops test framework harness."""
    harness = Harness(HAProxyCharm)
    yield harness
    harness.cleanup()
