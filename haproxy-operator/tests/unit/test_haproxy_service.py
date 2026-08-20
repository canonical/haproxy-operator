# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import pytest

from haproxy import HAPROXY_DH_PARAM, HAPROXY_DHCONFIG, HAProxyService
from state.charm_state import CharmState, ProxyMode


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


def _charm_state(log_hash_client_ip: bool) -> CharmState:
    return CharmState(
        mode=ProxyMode.LEGACY,
        enable_hsts=False,
        global_max_connection=1024,
        log_hash_client_ip=log_hash_client_ip,
    )


def test_render_default_config_hashes_client_ip_when_enabled():
    """
    arrange: Given a charm state with log_hash_client_ip enabled.
    act: Render the default haproxy configuration.
    assert: The config overrides log-format and error-log-format to hash the client IP.
    """
    config = HAProxyService().render_default_config(_charm_state(log_hash_client_ip=True))

    assert 'log-format "%[src,concat(,,\\"demo-salt-value\\"),sha2(256),hex]' in config
    assert 'error-log-format "%[src,concat(,,\\"demo-salt-value\\"),sha2(256),hex]' in config


def test_render_default_config_logs_plaintext_client_ip_when_disabled():
    """
    arrange: Given a charm state with log_hash_client_ip disabled.
    act: Render the default haproxy configuration.
    assert: No log-format overrides are set, so client IPs are logged in plaintext.
    """
    config = HAProxyService().render_default_config(_charm_state(log_hash_client_ip=False))

    assert "log-format" not in config
    assert "error-log-format" not in config
