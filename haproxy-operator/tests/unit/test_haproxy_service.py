# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import pytest

from haproxy import HAPROXY_DH_PARAM, HAPROXY_DHCONFIG, HAProxyService
from state.charm_state import LOG_HASHED_CLIENT_ADDRESS, CharmState, ProxyMode


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


@pytest.fixture(name="charm_state_factory")
def charm_state_factory_fixture():
    """Return a factory building a minimal CharmState rendering the default config."""

    def build(log_hash_client_ip: bool) -> CharmState:
        return CharmState(
            mode=ProxyMode.NOPROXY,
            enable_hsts=False,
            global_max_connection=1024,
            log_hash_client_ip=log_hash_client_ip,
        )

    return build


def test_render_default_config_hashes_client_ip_when_enabled(charm_state_factory):
    """
    arrange: Given a charm state with log_hash_client_ip enabled.
    act: Render the default haproxy configuration.
    assert: The config overrides log-format and error-log-format to hash the client IP.
    """
    config = HAProxyService().render_default_config(charm_state_factory(log_hash_client_ip=True))

    assert f'log-format "{LOG_HASHED_CLIENT_ADDRESS}' in config
    assert f'error-log-format "{LOG_HASHED_CLIENT_ADDRESS}' in config


def test_render_default_config_logs_plaintext_client_ip_when_disabled(charm_state_factory):
    """
    arrange: Given a charm state with log_hash_client_ip disabled.
    act: Render the default haproxy configuration.
    assert: No log-format overrides are set, so client IPs are logged in plaintext.
    """
    config = HAProxyService().render_default_config(charm_state_factory(log_hash_client_ip=False))

    assert "log-format" not in config
    assert "error-log-format" not in config
