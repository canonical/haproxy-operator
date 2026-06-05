# pylint: disable=import-error
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import logging
import os
import signal

# Ignoring import subprocess warning as we're using it with no user inputs
import subprocess  # nosec
import textwrap
import time
from pathlib import Path

import ops

# Ignoring here to make the linter happy as these modules will be available
# only inside the anycharm unit.
from any_charm_base import AnyCharmBase  # type: ignore
from haproxy_route_tcp import HaproxyRouteTcpRequirer, TCPHealthCheckType  # type: ignore

HAPROXY_ROUTE_TCP_RELATION = "require-haproxy-route-tcp"

TLS_ROOT = "/var/snap/ping-pong-tcp/common/"
CERT_PATH = f"{TLS_ROOT}server.crt"
KEY_PATH = f"{TLS_ROOT}server.key"
CNAME = "example.com"

logger = logging.getLogger()


class AnyCharm(AnyCharmBase):
    """haproxy-route requirer charm."""

    def __init__(self, *args, **kwargs):
        # We don't need to include *args and *kwargs in the docstring here.
        """Initialize the requirer charm."""
        super().__init__(*args, **kwargs)
        self._haproxy_route_tcp = HaproxyRouteTcpRequirer(self, HAPROXY_ROUTE_TCP_RELATION)
        self.framework.observe(self.on.config_changed, self.install)

    def install(self, _: ops.EventBase):
        """Install TCP server snap."""
        Path("v3.ext").write_text(
            textwrap.dedent(
                """
            authorityKeyIdentifier=keyid,issuer
            basicConstraints=CA:FALSE
            keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
            """
            ),
            "utf-8",
        )
        command = (
            "openssl genrsa -out ca.key 4096; "
            "openssl req -x509 -new -nodes -key ca.key -sha256 -days 1024 "
            f'-out ca.crt -subj "/C=FR/ST=CA/O=, Inc./CN={CNAME}"; '
            "openssl genrsa -out server.key 2048; "
            "openssl req -new -sha256 -key server.key "
            f'-subj "/C=FR/ST=P/O=, Inc./CN={CNAME}" -out server.csr; '
            "openssl x509 -req -days 365 -in server.csr -extfile v3.ext "
            "-CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt; "
            f"cp server.crt server.key {TLS_ROOT}; "
            "snap install ping-pong-tcp; "
            f"snap set ping-pong-tcp host=0.0.0.0"
        )
        # Ignoring subprocess warnings as we're using it with no user inputs
        subprocess.check_output(["/bin/bash", "-c", command])  # nosec
        self.unit.status = ops.ActiveStatus("TCP server ready (TCP).")

    def start_tls(self):
        """Start server in TLS mode."""
        command = f"snap set ping-pong-tcp tls.cert={CERT_PATH} tls.key={KEY_PATH}"
        # Ignoring subprocess warnings as we're using it with no user inputs
        subprocess.check_output(["/bin/bash", "-c", command])  # nosec
        self.unit.status = ops.ActiveStatus("TCP server ready (TLS).")

    def start_tcp(self):
        """Start server in plaintext mode."""
        # Ignoring subprocess warnings as we're using it with no user inputs
        subprocess.check_output(["/bin/bash", "-c", "snap unset ping-pong-tcp tls.cer tls.key"])  # nosec
        self.unit.status = ops.ActiveStatus("TCP server ready (TCP).")

    def update_relation(self):
        """Update haproxy-route-tcp relation data"""
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port=4444,
            backend_port=4000,
            sni=CNAME,
            check_type=TCPHealthCheckType.GENERIC,
            check_interval=60,
            check_rise=3,
            check_fall=3,
            check_send="ping\r\n",
            check_expect="pong",
        )

    def update_relation_with_sticky_sessions(self):
        """Update haproxy-route-tcp relation data with sticky sessions"""
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port=4444,
            backend_port=4000,
            sni=CNAME,
            check_type=TCPHealthCheckType.GENERIC,
            check_interval=60,
            check_rise=3,
            check_fall=3,
            check_send="ping\r\n",
            check_expect="pong",
            load_balancing_algorithm="source",
            load_balancing_consistent_hashing=True,
            retry_count=3,
            retry_redispatch=True,
        )

    def update_relation_with_timeouts(self):
        """Update haproxy-route-tcp relation data with timeouts"""
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port=4444,
            backend_port=4000,
            sni=CNAME,
            check_type=TCPHealthCheckType.GENERIC,
            check_interval=60,
            check_rise=3,
            check_fall=3,
            check_send="ping\r\n",
            check_expect="pong",
            server_timeout=10,
            connect_timeout=5,
            queue_timeout=2,
        )

    def update_relation_with_proxy_protocol(self):
        """Update haproxy-route-tcp relation data with proxy protocol enabled."""
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port=4444,
            backend_port=4000,
            proxy_protocol=True,
            sni=CNAME,
        )

    def update_relation_with_port_range(self):
        """Update haproxy-route-tcp relation data with port_range.

        Uses port_range for 1-to-1 frontend-to-backend port mapping.
        Uses a small range (10500-10502) to verify range expansion works.
        """
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port_range="10500-10502",
        )

    def start_port_range_servers(self):
        """Start TCP echo servers on each port in the port_range.

        For port_range mode, HAProxy connects to the backend on the same
        port as the frontend (1-to-1 mapping). We need a listener on each
        port in the range so that end-to-end connectivity can be verified.

        Writes a small Python TCP server script and starts it as a
        background process via nohup.
        """
        server_script = textwrap.dedent("""\
            import socket
            import threading
            import time
            import os
            import signal

            def handle_client(conn):
                try:
                    data = conn.recv(1024)
                    if b"ping" in data.lower():
                        conn.sendall(b"pong\\n")
                    else:
                        conn.sendall(b"echo: " + data)
                except Exception:
                    pass
                finally:
                    conn.close()

            def start_server(port):
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("0.0.0.0", port))
                srv.listen(5)
                while True:
                    conn, _ = srv.accept()
                    threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

            PORT_RANGE_START = 10500
            PORT_RANGE_END = 10502

            # Write PID file so we can kill the process later
            with open("/tmp/port_range_server.pid", "w") as f:
                f.write(str(os.getpid()))

            for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
                t = threading.Thread(target=start_server, args=(port,), daemon=True)
                t.start()

            # Keep main thread alive
            signal.pause()
        """)
        Path("/tmp/port_range_server.py").write_text(server_script, "utf-8")
        # Start as background process
        subprocess.Popen(  # nosec
            ["nohup", "python3", "/tmp/port_range_server.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give servers a moment to bind
        time.sleep(1)
        self.unit.status = ops.ActiveStatus("TCP servers ready (port range).")

    def stop_port_range_servers(self):
        """Stop the background TCP echo servers started for port_range testing."""
        pid_file = Path("/tmp/port_range_server.pid")
        if pid_file.exists():
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            pid_file.unlink()
        self.unit.status = ops.ActiveStatus("TCP server ready.")
