# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from haproxy import (
    HAPROXY_DH_PARAM,
    HAPROXY_DHCONFIG,
    HAPROXY_LOGROTATE_CONFIG,
    LOGROTATE_TIMER_OVERRIDE,
    HAProxyService,
    render_file,
)


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
    mkdir_mock = MagicMock()
    monkeypatch.setattr("haproxy.Path.mkdir", mkdir_mock)
    systemd_mock = MagicMock()
    monkeypatch.setattr("haproxy.systemd", systemd_mock)

    haproxy_service = HAProxyService()
    haproxy_service.install()

    apt_add_package_mock.assert_called_once()
    assert render_file_mock.call_count == 3
    render_file_mock.assert_any_call(HAPROXY_DHCONFIG, HAPROXY_DH_PARAM, 0o644)
    render_file_mock.assert_any_call(
        HAPROXY_LOGROTATE_CONFIG,
        HAProxyService()._render_to_string("haproxy.logrotate.j2", {}),
        0o644,
        user="root",
    )
    render_file_mock.assert_any_call(
        LOGROTATE_TIMER_OVERRIDE,
        "[Timer]\nOnCalendar=\nOnCalendar=hourly\nAccuracySec=1min\n",
        0o644,
        user="root",
    )
    mkdir_mock.assert_called_once_with(parents=True, exist_ok=True)
    systemd_mock.daemon_reload.assert_called_once_with()
    systemd_mock.service_enable.assert_called_once_with("logrotate.timer")
    systemd_mock.service_restart.assert_called_once_with("logrotate.timer")


def test_install_logrotate_policy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """
    arrange: Given a service with package installation and systemd calls mocked.
    act: Install twice, as on install and upgrade.
    assert: The policy and hourly timer override are written with safe permissions.
    """
    monkeypatch.setattr("haproxy.run", MagicMock())
    monkeypatch.setattr("haproxy.apt.add_package", MagicMock())
    monkeypatch.setattr("haproxy.systemd", MagicMock())
    monkeypatch.setattr("haproxy.HAPROXY_DHCONFIG", tmp_path / "ffdhe2048.txt")
    logrotate_config = tmp_path / "haproxy"
    timer_override = tmp_path / "logrotate.timer.d" / "override.conf"
    monkeypatch.setattr("haproxy.HAPROXY_LOGROTATE_CONFIG", logrotate_config)
    monkeypatch.setattr("haproxy.LOGROTATE_TIMER_OVERRIDE", timer_override)
    owner = MagicMock(pw_uid=0, pw_gid=0)
    monkeypatch.setattr("haproxy.pwd.getpwnam", MagicMock(return_value=owner))
    chown_mock = MagicMock()
    monkeypatch.setattr("haproxy.os.chown", chown_mock)

    service = HAProxyService()
    service.install()
    service.install()

    assert logrotate_config.read_text() == (
        "/var/log/haproxy.log {\n"
        "    daily\n"
        "    rotate 7\n"
        "    maxsize 1G\n"
        "    missingok\n"
        "    notifempty\n"
        "    compress\n"
        "    delaycompress\n"
        "    postrotate\n"
        "        [ ! -x /usr/lib/rsyslog/rsyslog-rotate ] || /usr/lib/rsyslog/rsyslog-rotate\n"
        "    endscript\n"
        "}\n"
    )
    assert timer_override.read_text() == (
        "[Timer]\nOnCalendar=\nOnCalendar=hourly\nAccuracySec=1min\n"
    )
    assert logrotate_config.stat().st_mode & 0o777 == 0o644
    assert timer_override.stat().st_mode & 0o777 == 0o644
    chown_mock.assert_any_call(logrotate_config, uid=0, gid=0)
    chown_mock.assert_any_call(timer_override, uid=0, gid=0)


@pytest.mark.parametrize("user", ["haproxy", "root"])
def test_render_file_owner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user: str):
    """
    arrange: Given a file to render and a requested owner.
    act: Render with default or explicit root ownership.
    assert: The requested user's UID and GID are used.
    """
    owner = MagicMock(pw_uid=123, pw_gid=456)
    getpwnam_mock = MagicMock(return_value=owner)
    monkeypatch.setattr("haproxy.pwd.getpwnam", getpwnam_mock)
    chown_mock = MagicMock()
    monkeypatch.setattr("haproxy.os.chown", chown_mock)
    path = tmp_path / "config"

    if user == "root":
        render_file(path, "content", 0o644, user=user)
    else:
        render_file(path, "content", 0o644)

    getpwnam_mock.assert_called_once_with(user)
    chown_mock.assert_called_once_with(path, uid=123, gid=456)


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
