# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import pytest

import legacy
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


def _legacy_tcp_service(service_options):
    return {
        "myapp": {
            "service_name": "myapp",
            # nosec B104: test fixture, the host value is never used to bind a socket
            "service_host": "0.0.0.0",
            "service_port": 9000,
            "service_options": service_options,
            "servers": [["s1", "10.0.0.1", 9000, "check"]],
        }
    }


def test_legacy_tcp_service_with_tcplog_gets_hashed_log_format():
    """
    arrange: A legacy TCP service that sets option tcplog (which would override the
        defaults log-format with the plaintext TCP default).
    act: Generate its config stanza with a hashed TCP log format.
    assert: The stanza sets the hashed log-format explicitly on the frontend.
    """
    tcp_log_format = CharmState(
        mode=ProxyMode.LEGACY, enable_hsts=False, global_max_connection=1024
    ).tcp_log_format
    stanza = legacy.generate_service_config(
        _legacy_tcp_service(["mode tcp", "option tcplog"]), tcp_log_format
    )[0]

    assert 'log-format "%[src,concat(,,\\"demo-salt-value\\"),sha2(256),hex]' in stanza


def test_legacy_tcp_service_without_tcplog_inherits_defaults_log_format():
    """
    arrange: A legacy TCP service that does not set option tcplog (it inherits the
        defaults log-format, preserving its log structure).
    act: Generate its config stanza with a hashed TCP log format.
    assert: No log-format is injected, so it keeps the defaults structure.
    """
    tcp_log_format = CharmState(
        mode=ProxyMode.LEGACY, enable_hsts=False, global_max_connection=1024
    ).tcp_log_format
    stanza = legacy.generate_service_config(_legacy_tcp_service(["mode tcp"]), tcp_log_format)[0]

    assert "log-format" not in stanza
