# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the keepalived service."""

from unittest.mock import MagicMock

import pytest

from keepalived import KeepalivedService


def test_install(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a KeepalivedService with keepalived absent and the apt library mocked.
    act: Call KeepalivedService.install().
    assert: The keepalived package is installed once.
    """
    monkeypatch.setattr("keepalived.shutil.which", MagicMock(return_value=None))
    apt_add_package_mock = MagicMock()
    monkeypatch.setattr("keepalived.apt.add_package", apt_add_package_mock)

    KeepalivedService().install()

    apt_add_package_mock.assert_called_once_with(package_names=["keepalived"], update_cache=True)


def test_install_does_nothing_when_already_present(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a KeepalivedService with keepalived already installed.
    act: Call KeepalivedService.install().
    assert: The apt library is not called.
    """
    monkeypatch.setattr("keepalived.shutil.which", MagicMock(return_value="/usr/sbin/keepalived"))
    apt_add_package_mock = MagicMock()
    monkeypatch.setattr("keepalived.apt.add_package", apt_add_package_mock)

    KeepalivedService().install()

    apt_add_package_mock.assert_not_called()
