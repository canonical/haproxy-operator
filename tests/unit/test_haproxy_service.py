# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""
from unittest.mock import MagicMock

import pytest

import haproxy


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
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.HAProxyService._render_file", render_file_mock)

    haproxy_service = haproxy.HAProxyService()
    haproxy_service.install()

    apt_update_mock.assert_called_once()
    apt_add_package_mock.assert_called_once()
    render_file_mock.assert_called_once_with(
        haproxy.HAPROXY_DHCONFIG, haproxy.HAPROXY_DH_PARAM, 0o644
    )
