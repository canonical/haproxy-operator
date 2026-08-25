# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for the log-hash-client-ip config option."""

import hashlib
import socket
import ssl
import uuid
from ipaddress import ip_address

import jubilant
import pytest
import requests

from .conftest import all_active_and_idle
from .helper import get_unit_address, get_unit_ip_address

LOG_HASH_SALT = "demo-salt-value"


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


@pytest.fixture(name="log_hash_secret")
def log_hash_secret_fixture(
    configured_application_with_tls: str,
    juju: jubilant.Juju,
):
    """Provide a granted log hash secret and restore the application configuration."""
    secret_uri = juju.add_secret(
        f"haproxy-log-hash-{uuid.uuid4().hex}",
        {"salt": LOG_HASH_SALT},
    )
    juju.grant_secret(secret_uri, configured_application_with_tls)
    yield secret_uri

    juju.config(configured_application_with_tls, {"log-hash-client-ip": "false"})
    juju.cli("config", configured_application_with_tls, "--reset", "log-hash-salt")
    juju.wait(lambda status: all_active_and_idle(status, configured_application_with_tls))
    juju.remove_secret(secret_uri)


def test_log_hash_client_ip(
    configured_application_with_tls: str,
    any_charm_haproxy_route_tcp_requirer: str,
    log_hash_secret,
    juju: jubilant.Juju,
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
    juju.config(application, {"log-hash-client-ip": "false"})
    juju.wait(lambda status: all_active_and_idle(status, application))

    plaintext_marker = f"plaintext-{uuid.uuid4().hex}"
    response = requests.get(f"{address}/?{plaintext_marker}", timeout=10)
    assert response.status_code == 200
    client_ip = _last_client_field(juju, unit, plaintext_marker).rsplit(":", 1)[0]
    ip_address(client_ip)

    juju.config(
        application,
        {
            "log-hash-client-ip": "true",
            "log-hash-salt": str(log_hash_secret),
        },
    )
    juju.wait(lambda status: all_active_and_idle(status, application))

    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(client_ip.encode() + LOG_HASH_SALT.encode()).hexdigest().upper()
    response = requests.get(f"{address}/?default-hash", verify=False, timeout=30)  # nosec
    assert response.status_code == 200
    hashed_http_client = _last_client_field(juju, unit, "default-hash")
    assert hashed_http_client.startswith(f"{expected_hash}:")
    assert not hashed_http_client.startswith(f"{client_ip}:")

    tcp_relation = (
        f"{application}:haproxy-route-tcp",
        any_charm_haproxy_route_tcp_requirer,
    )
    juju.integrate(*tcp_relation)
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "update_relation"},
    )
    juju.wait(
        lambda status: all_active_and_idle(
            status,
            application,
            any_charm_haproxy_route_tcp_requirer,
        )
    )

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
    assert not hashed_tcp_client.startswith(f"{client_ip}:")
