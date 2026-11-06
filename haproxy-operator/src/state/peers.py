# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy peers information mixin for charm state components."""

from pydantic import IPvAnyAddress

HAPROXY_PEER_PORT = 10000


class PeersInformation:
    """Mixin providing HAProxy peer formatting properties.

    Subclasses must define a ``peers: list[IPvAnyAddress]`` field.

    Attrs:
        formatted_peer_entries: Pre-rendered peer entry strings for the HAProxy config.
        peer_tcp_port: The TCP port used for HAProxy peer communication.
    """

    peers: list[IPvAnyAddress]

    @property
    def formatted_peer_entries(self) -> list[str]:
        """Format peer IP addresses into HAProxy peer entry strings.

        Each entry is formatted as ``<name> <address>:<port>`` where ``<name>``
        is derived from the IP address with non-alphanumeric characters replaced
        by hyphens.

        Returns:
            list[str]: Formatted peer entry strings.
        """
        entries: list[str] = []
        for addr in self.peers:
            name = str(addr).replace(".", "-").replace(":", "-")
            entries.append(f"{name} {addr}:{HAPROXY_PEER_PORT}")
        return entries

    @property
    def peer_tcp_port(self) -> int:
        """Return the TCP port used for HAProxy peer communication.

        Returns:
            int: The peer TCP port.
        """
        return HAPROXY_PEER_PORT
