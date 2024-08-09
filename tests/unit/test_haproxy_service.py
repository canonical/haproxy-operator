# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""
from unittest.mock import MagicMock

import pytest

from haproxy import HAProxyService


@pytest.mark.usefixtures("systemd_mock")
def test_deploy(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a HAProxyService class with mocked apt library methods.
    act: Call haproxy_service.install().
    assert: The apt mocks are called once.
    """
    apt_update_mock = MagicMock()
    monkeypatch.setattr("charms.operator_libs_linux.v0.apt.update", apt_update_mock)
    apt_add_package_mock = MagicMock()
    monkeypatch.setattr("charms.operator_libs_linux.v0.apt.add_package", apt_add_package_mock)
    haproxy_service = HAProxyService()

    haproxy_service.install()

    apt_update_mock.assert_called_once()
    apt_add_package_mock.assert_called_once()
