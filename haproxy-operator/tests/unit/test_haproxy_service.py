# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from dataclasses import replace
from subprocess import CalledProcessError
from unittest.mock import MagicMock

import pytest

from haproxy import (
    HAPROXY_DH_PARAM,
    HAPROXY_DHCONFIG,
    HAProxyService,
    HaproxyValidateConfigError,
)


@pytest.mark.usefixtures("systemd_mock")
def test_deploy(monkeypatch: pytest.MonkeyPatch, tmp_path):
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
    certs_dir = tmp_path / "certs"
    monkeypatch.setattr("haproxy.HAPROXY_CERTS_DIR", certs_dir)

    haproxy_service = HAProxyService()
    haproxy_service.install()

    apt_add_package_mock.assert_called_once()
    render_file_mock.assert_called_once_with(HAPROXY_DHCONFIG, HAPROXY_DH_PARAM, 0o644)
    assert certs_dir.is_dir()


def test_validate_config_logs_command_output(monkeypatch: pytest.MonkeyPatch, caplog):
    error = CalledProcessError(
        returncode=1,
        cmd=["/usr/sbin/haproxy", "-f", "/etc/haproxy/haproxy.cfg", "-c"],
        stderr=b"No SSL certificate specified",
    )
    monkeypatch.setattr("haproxy.subprocess.run", MagicMock(side_effect=error))

    with pytest.raises(HaproxyValidateConfigError):
        HAProxyService()._validate_haproxy_config()

    assert "No SSL certificate specified" in caplog.text


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
