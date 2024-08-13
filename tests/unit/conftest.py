# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from charm import HAProxyCharm


@pytest.fixture(scope="function", name="harness")
def harness_fixture():
    """Enable ops test framework harness."""
    harness = Harness(HAProxyCharm)
    yield harness
    harness.cleanup()


@pytest.fixture(scope="function", name="systemd_mock")
def systemd_mock_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock systemd lib methods."""
    monkeypatch.setattr("charms.operator_libs_linux.v1.systemd.service_restart", MagicMock())
    monkeypatch.setattr(
        "charms.operator_libs_linux.v1.systemd.service_running", MagicMock(return_value=True)
    )
