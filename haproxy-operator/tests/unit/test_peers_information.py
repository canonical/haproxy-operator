# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the PeersInformation mixin."""

from ipaddress import IPv4Address, IPv6Address
from typing import cast

from pydantic import IPvAnyAddress

from state.peers import HAPROXY_PEER_PORT, PeersInformation


class _PeersInfoStub(PeersInformation):
    """Minimal concrete class for testing the mixin."""

    def __init__(self, peers: list[IPvAnyAddress]):
        self.peers = peers


def test_formatted_peer_entries_ipv4():
    """
    arrange: A PeersInformation instance with IPv4 peer addresses.
    act: Access the formatted_peer_entries property.
    assert: Each entry has the format '<name> <address>:<port>'.
    """
    info = _PeersInfoStub(
        [
            cast(IPvAnyAddress, IPv4Address("10.68.79.144")),
            cast(IPvAnyAddress, IPv4Address("192.168.1.10")),
        ]
    )

    assert info.formatted_peer_entries == [
        f"10-68-79-144 10.68.79.144:{HAPROXY_PEER_PORT}",
        f"192-168-1-10 192.168.1.10:{HAPROXY_PEER_PORT}",
    ]


def test_formatted_peer_entries_ipv6():
    """
    arrange: A PeersInformation instance with an IPv6 peer address.
    act: Access the formatted_peer_entries property.
    assert: Colons are replaced by hyphens in the peer name.
    """
    info = _PeersInfoStub([cast(IPvAnyAddress, IPv6Address("fd42:bc01:a5e3:f4e2::1"))])

    assert info.formatted_peer_entries == [
        f"fd42-bc01-a5e3-f4e2--1 fd42:bc01:a5e3:f4e2::1:{HAPROXY_PEER_PORT}",
    ]


def test_formatted_peer_entries_empty():
    """
    arrange: A PeersInformation instance with no peers.
    act: Access the formatted_peer_entries property.
    assert: Returns an empty list.
    """
    info = _PeersInfoStub([])

    assert info.formatted_peer_entries == []


def test_peer_tcp_port():
    """
    arrange: A PeersInformation instance.
    act: Access the peer_tcp_port property.
    assert: Returns the constant HAPROXY_PEER_PORT.
    """
    info = _PeersInfoStub([])

    assert info.peer_tcp_port == HAPROXY_PEER_PORT
