# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for client IP log hashing."""

import hashlib
import socket
import ssl
import uuid
from ipaddress import ip_address

import jubilant
import pytest
import requests

from .conftest import LOG_HASH_SALT, all_active_and_idle
from .helper import get_unit_address, get_unit_ip_address


def _last_client_field(juju: jubilant.Juju, unit: str, marker: str) -> str:
    """Return the client address field (IP:port) of the most recent haproxy access log.

    Logs are read from the journal rather than /var/log/haproxy.log because
    rsyslog file routing does not work in all environments (e.g. nested
    containers), while journald always captures haproxy's syslog output.
    """
    logs = juju.ssh(unit, "journalctl -u haproxy --no-pager -n 50")
    lines = [line for line in logs.splitlines() if " haproxy" in line and marker in line]
    assert lines, "no haproxy access log lines found"

    message = lines[-1].split("haproxy", 1)[1].split(None, 1)[1]
    return message.split()[0]


def test_client_ip_hash_salt(
    configured_application_with_tls: str,
    log_hash_secret,
    juju: jubilant.Juju,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy the charm.
    act: Toggle client IP hashing and send HTTP and TCP requests.
    assert: Client IPs are plaintext when disabled and salted hashes when enabled.
    """
    application = configured_application_with_tls
    unit = f"{application}/0"
    juju.wait(lambda status: all_active_and_idle(status, application))
    address = get_unit_address(juju, application)

    juju.config(
        application,
        {"client-ip-hash-salt": str(log_hash_secret)},
    )
    juju.wait(lambda status: all_active_and_idle(status, application))

    response = requests.get(f"{address}/?default-hash", verify=False, timeout=30)  # nosec
    assert response.status_code == 200
    hashed_http_client = _last_client_field(juju, unit, "default-hash")

    juju.cli("config", application, "--reset", "client-ip-hash-salt")
    juju.wait(lambda status: all_active_and_idle(status, application))

    restored_plaintext_marker = f"restored-plaintext-{uuid.uuid4().hex}"
    response = requests.get(f"{address}/?{restored_plaintext_marker}", timeout=10)
    assert response.status_code == 200
    restored_client_ip = _last_client_field(juju, unit, restored_plaintext_marker).rsplit(":", 1)[
        0
    ]
    ip_address(restored_client_ip)

    # HAProxy's hex converter outputs uppercase.
    expected_hash = (
        hashlib.sha256(restored_client_ip.encode() + LOG_HASH_SALT.encode()).hexdigest().upper()
    )
    assert hashed_http_client.startswith(f"{expected_hash}:")
    assert not hashed_http_client.startswith(f"{restored_client_ip}:")

    juju.config(
        application,
        {"client-ip-hash-salt": str(log_hash_secret)},
    )
    juju.wait(lambda status: all_active_and_idle(status, application))

    request.getfixturevalue("haproxy_route_tcp_relation")

    haproxy_ip_address = get_unit_ip_address(juju, application)
    context = ssl._create_unverified_context()  # pylint: disable=protected-access  # nosec
    with (
        socket.create_connection((str(haproxy_ip_address), 4444), timeout=30) as sock,
        context.wrap_socket(sock, server_hostname="example.com") as secure_socket,
    ):
        secure_socket.sendall(b"ping")
        assert b"pong" in secure_socket.read()

    hashed_tcp_client = _last_client_field(juju, unit, "haproxy_route_tcp_4444")
    assert hashed_tcp_client.startswith(f"{expected_hash}:")
    assert not hashed_tcp_client.startswith(f"{restored_client_ip}:")
