# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from haproxy import HAPROXY_DH_PARAM, HAPROXY_DHCONFIG, HAProxyService


@pytest.mark.usefixtures("systemd_mock")
def test_deploy(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a HAProxyService class with mocked apt library methods.
    act: Call haproxy_service.install().
    assert: The apt mocks are called once.
    """
    apt_add_package_mock = MagicMock()
    monkeypatch.setattr("charms.operator_libs_linux.v0.apt.add_package", apt_add_package_mock)
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    monkeypatch.setattr("haproxy.run", MagicMock())

    haproxy_service = HAProxyService()
    haproxy_service.install()

    apt_add_package_mock.assert_called_once()
    render_file_mock.assert_called_once_with(HAPROXY_DHCONFIG, HAPROXY_DH_PARAM, 0o644)


def test_render_default_config_hashes_client_ip_when_enabled(hashed_charm_state):
    """
    arrange: Given a charm state with hash_client_ip_in_logs enabled.
    act: Render the default haproxy configuration.
    assert: The config overrides log-format and error-log-format to hash the client IP.
    """
    config = HAProxyService().render_default_config(hashed_charm_state)

    assert f'log-format "{hashed_charm_state.log_hash_client_address}' in config
    assert f'error-log-format "{hashed_charm_state.log_hash_client_address}' in config


def test_render_default_config_logs_plaintext_client_ip_when_disabled(hashed_charm_state):
    """
    arrange: Given a charm state without a client IP hash salt.
    act: Render the default haproxy configuration.
    assert: No log-format overrides are set, so client IPs are logged in plaintext.
    """
    charm_state = replace(hashed_charm_state, client_ip_hash_salt=None)
    config = HAProxyService().render_default_config(charm_state)

    assert "log-format" not in config
    assert "error-log-format" not in config
