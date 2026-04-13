# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from typing import cast
from unittest.mock import MagicMock

import pytest
from pydantic import IPvAnyAddress

from haproxy import (
    HAPROXY_DH_PARAM,
    HAPROXY_DHCONFIG,
    HAPROXY_PEER_PORT,
    HAProxyService,
    _format_peer_entries,
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

    haproxy_service = HAProxyService()
    haproxy_service.install()

    apt_add_package_mock.assert_called_once()
    render_file_mock.assert_called_once_with(HAPROXY_DHCONFIG, HAPROXY_DH_PARAM, 0o644)


def test_format_peer_entries_ipv4():
    """
    arrange: A list of IPv4 peer addresses.
    act: Call _format_peer_entries.
    assert: Each entry has the format '<name> <address>:<port>'.
    """
    peers = [cast(IPvAnyAddress, "10.68.79.144"), cast(IPvAnyAddress, "192.168.1.10")]

    result = _format_peer_entries(peers)

    assert result == [
        f"10-68-79-144 10.68.79.144:{HAPROXY_PEER_PORT}",
        f"192-168-1-10 192.168.1.10:{HAPROXY_PEER_PORT}",
    ]


def test_format_peer_entries_empty():
    """
    arrange: An empty list of peer addresses.
    act: Call _format_peer_entries.
    assert: Returns an empty list.
    """
    result = _format_peer_entries([])

    assert result == []
