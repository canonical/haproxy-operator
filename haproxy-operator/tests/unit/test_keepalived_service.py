# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the keepalived service."""

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
