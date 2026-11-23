# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the keepalived service."""

from ipaddress import ip_interface
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from keepalived import KeepalivedService


@pytest.mark.parametrize(
    "which_return,expected_packages",
    [
        pytest.param(None, ["keepalived"], id="not-installed"),
        pytest.param("/usr/sbin/keepalived", None, id="already-installed"),
    ],
)
def test_install(
    monkeypatch: pytest.MonkeyPatch,
    which_return: str | None,
    expected_packages: list[str] | None,
):
    """
    arrange: Given a KeepalivedService and the apt library mocked.
    act: Call KeepalivedService.install().
    assert: The keepalived package is installed only when it is absent.
    """
    monkeypatch.setattr("keepalived.shutil.which", MagicMock(return_value=which_return))
    apt_add_package_mock = MagicMock()
    monkeypatch.setattr("keepalived.apt.add_package", apt_add_package_mock)

    KeepalivedService().install()

    if expected_packages is None:
        apt_add_package_mock.assert_not_called()
    else:
        apt_add_package_mock.assert_called_once_with(
            package_names=expected_packages, update_cache=True
        )


def _patch_keepalived_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the keepalived configuration to a temporary directory."""
    config_file = tmp_path / "keepalived.conf"
    monkeypatch.setattr("keepalived.KEEPALIVED_CONFIG", config_file)
    monkeypatch.setattr("keepalived.KEEPALIVED_CONFIG_DIR", tmp_path)
    return config_file


def test_reconcile_renders_config_and_starts_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """
    arrange: Given a virtual IP and keepalived not running.
    act: Call KeepalivedService.reconcile().
    assert: The configuration contains the VIP and interface, and the service is started.
    """
    config_file = _patch_keepalived_paths(monkeypatch, tmp_path)
    monkeypatch.setattr("keepalived.get_network_interface", MagicMock(return_value="eth0"))
    service_running_mock = MagicMock(return_value=False)
    service_start_mock = MagicMock()
    service_reload_mock = MagicMock()
    monkeypatch.setattr("keepalived.systemd.service_running", service_running_mock)
    monkeypatch.setattr("keepalived.systemd.service_start", service_start_mock)
    monkeypatch.setattr("keepalived.systemd.service_reload", service_reload_mock)

    KeepalivedService().reconcile(ip_interface("192.168.1.100/24"))

    config = config_file.read_text()
    assert "interface eth0" in config
    assert "192.168.1.100/24 dev eth0" in config
    service_start_mock.assert_called_once_with("keepalived")
    service_reload_mock.assert_not_called()


def test_reconcile_reloads_service_only_when_config_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """
    arrange: Given a virtual IP and keepalived already running.
    act: Call KeepalivedService.reconcile() twice.
    assert: The service is reloaded only the first time the configuration changes.
    """
    config_file = _patch_keepalived_paths(monkeypatch, tmp_path)
    config_file.write_text("old config")
    monkeypatch.setattr("keepalived.get_network_interface", MagicMock(return_value="eth0"))
    service_reload_mock = MagicMock()
    monkeypatch.setattr("keepalived.systemd.service_running", MagicMock(return_value=True))
    monkeypatch.setattr("keepalived.systemd.service_start", MagicMock())
    monkeypatch.setattr("keepalived.systemd.service_reload", service_reload_mock)

    service = KeepalivedService()
    service.reconcile(ip_interface("192.168.1.100/24"))
    service.reconcile(ip_interface("192.168.1.100/24"))

    service_reload_mock.assert_called_once_with("keepalived")


def test_reconcile_without_vip_stops_service_and_removes_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """
    arrange: Given an existing configuration and a running keepalived service.
    act: Call KeepalivedService.reconcile() without a virtual IP.
    assert: The configuration is removed and the service is stopped.
    """
    config_file = _patch_keepalived_paths(monkeypatch, tmp_path)
    config_file.write_text("config")
    service_stop_mock = MagicMock()
    monkeypatch.setattr("keepalived.systemd.service_running", MagicMock(return_value=True))
    monkeypatch.setattr("keepalived.systemd.service_stop", service_stop_mock)

    KeepalivedService().reconcile(None)

    assert not config_file.exists()
    service_stop_mock.assert_called_once_with("keepalived")
