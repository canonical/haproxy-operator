# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from charm import HAProxyCharm


@pytest.fixture(scope="function", name="harness")
def harness_fixture(monkeypatch: pytest.MonkeyPatch):
    """Enable ops test framework harness."""
    monkeypatch.setattr(HAProxyCharm, "_get_unit_address", MagicMock(return_value="10.0.0.1"))
    harness = Harness(HAProxyCharm)
    yield harness
    harness.cleanup()
