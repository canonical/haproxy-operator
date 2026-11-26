# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the keepalived service."""

from ipaddress import ip_interface
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from keepalived import (
    KeepalivedConfigurationError,
    KeepalivedService,
    get_network_interface,
)


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


@pytest.mark.parametrize(
    "which_return,check_output_return,check_output_exception",
    [
        pytest.param(None, None, None, id="missing-ip-command"),
        pytest.param(
            "/usr/sbin/ip",
            None,
            FileNotFoundError("ip route get failed"),
            id="route-lookup-failed",
        ),
        pytest.param("/usr/sbin/ip", "not json", None, id="invalid-json"),
        pytest.param("/usr/sbin/ip", "[]", None, id="empty-route"),
        pytest.param("/usr/sbin/ip", '[{"gateway": "192.168.1.1"}]', None, id="missing-device"),
    ],
)
def test_get_network_interface_raises(
    monkeypatch: pytest.MonkeyPatch,
    which_return: str | None,
    check_output_return: str | None,
    check_output_exception: Exception | None,
):
    """
    arrange: Given an environment where the interface cannot be determined.
    act: Call get_network_interface().
    assert: A KeepalivedConfigurationError is raised.
    """
    monkeypatch.setattr("keepalived.shutil.which", MagicMock(return_value=which_return))
    monkeypatch.setattr(
        "keepalived.subprocess.check_output",
        MagicMock(return_value=check_output_return, side_effect=check_output_exception),
    )

    with pytest.raises(KeepalivedConfigurationError):
        get_network_interface("192.168.1.100")


def test_get_network_interface_returns_device(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a successful route lookup.
    act: Call get_network_interface().
    assert: The device from the route lookup is returned.
    """
    monkeypatch.setattr("keepalived.shutil.which", MagicMock(return_value="/usr/sbin/ip"))
    monkeypatch.setattr(
        "keepalived.subprocess.check_output",
        MagicMock(return_value='[{"dev": "eth0"}]'),
    )

    assert get_network_interface("192.168.1.100") == "eth0"


@pytest.mark.parametrize(
    "vip,initial_config,service_running,reconcile_times,"
    "expected_start_calls,expected_reload_calls,expected_stop_calls",
    [
        pytest.param(
            "192.168.1.100/24",
            None,
            False,
            1,
            1,
            0,
            0,
            id="starts-when-stopped",
        ),
        pytest.param(
            "192.168.1.100/24",
            "old config",
            True,
            2,
            0,
            1,
            0,
            id="reloads-once-when-config-changes",
        ),
        pytest.param(
            None,
            "config",
            True,
            1,
            0,
            0,
            1,
            id="stops-when-vip-removed",
        ),
    ],
)
def test_reconcile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    vip: str | None,
    initial_config: str | None,
    service_running: bool,
    reconcile_times: int,
    expected_start_calls: int,
    expected_reload_calls: int,
    expected_stop_calls: int,
):
    """
    arrange: Given a virtual IP (or none) and a keepalived service in an initial state.
    act: Call KeepalivedService.reconcile().
    assert: The configuration and the service are reconciled as expected.
    """
    config_file = _patch_keepalived_paths(monkeypatch, tmp_path)
    if initial_config is not None:
        config_file.write_text(initial_config)
    monkeypatch.setattr("keepalived.get_network_interface", MagicMock(return_value="eth0"))
    service_start_mock = MagicMock()
    service_reload_mock = MagicMock()
    service_stop_mock = MagicMock()
    monkeypatch.setattr(
        "keepalived.systemd.service_running", MagicMock(return_value=service_running)
    )
    monkeypatch.setattr("keepalived.systemd.service_start", service_start_mock)
    monkeypatch.setattr("keepalived.systemd.service_reload", service_reload_mock)
    monkeypatch.setattr("keepalived.systemd.service_stop", service_stop_mock)

    service = KeepalivedService()
    for _ in range(reconcile_times):
        service.reconcile(ip_interface(vip) if vip else None)

    if vip is None:
        assert not config_file.exists()
    else:
        config = config_file.read_text()
        assert "interface eth0" in config
        assert f"{vip} dev eth0" in config
    assert service_start_mock.call_count == expected_start_calls
    assert service_reload_mock.call_count == expected_reload_calls
    assert service_stop_mock.call_count == expected_stop_calls
