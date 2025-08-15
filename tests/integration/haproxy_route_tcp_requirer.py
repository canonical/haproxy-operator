# pylint: disable=import-error
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import socket
import threading

import ops
from any_charm_base import AnyCharmBase  # type: ignore
from haproxy_route_tcp import HaproxyRouteTcpRequirer, TCPRateLimitPolicy  # type: ignore

HAPROXY_ROUTE_TCP_RELATION = "require-haproxy-route-tcp"
TCP_LISTEN_PORT = 4000

def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", TCP_LISTEN_PORT))
    s.listen()
    conn, _ = s.accept()
    with conn:
        data = str(conn.recv(5))
        if "ping" in data:
            conn.sendall(b"pong\n")
    s.close()

class AnyCharm(AnyCharmBase):
    """haproxy-route requirer charm."""

    def __init__(self, *args, **kwargs):
        """Initialize the requirer charm."""  # noqa
        super().__init__(*args, **kwargs)
        self._haproxy_route_tcp = HaproxyRouteTcpRequirer(self, HAPROXY_ROUTE_TCP_RELATION)
        self.unit.status = ops.ActiveStatus("Server not active")

    def start_server(self):
        """Start TCP server."""
        self.thread = threading.Thread(target=tcp_server, daemon=True)
        self.thread.start()
        self.unit.status = ops.ActiveStatus("Server ready")

    def stop_server(self):
        """Stop the TCP server thread.
        
        join() will block until the thread returns. Run this after the server
        has handled a connection.
        """
        self.thread.join(10.0)
        self.unit.status = ops.ActiveStatus("Server not active")

    def update_relation_data(self):
        self._haproxy_route_tcp.configure_port(4000).configure_backend_port(
            5000
        ).configure_health_check(60, 5, 5).configure_rate_limit(
            10, TCPRateLimitPolicy.SILENT
        ).update_relation_data()
