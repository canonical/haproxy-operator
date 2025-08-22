# pylint: disable=import-error
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import logging
# Ignoring import subprocess warning as we're using it with no user inputs
import subprocess  # nosec
import textwrap
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
        """Initialize the requirer charm."""  # noqa
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
        subprocess.check_output(
            ["/bin/bash", "-c", "snap unset ping-pong-tcp tls.cer tls.key"]
        )  # nosec
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
