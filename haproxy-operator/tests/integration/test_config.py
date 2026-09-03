# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for client IP log hashing."""

import hashlib
import socket
import ssl
import time
import uuid
from ipaddress import ip_address

import jubilant
import pytest
import requests

from .conftest import LOG_HASH_SALT, all_active_and_idle
from .helper import get_unit_address, get_unit_ip_address


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

    hashed_http_client = _request_until_logged(
        juju,
        unit,
        address,
        "default-hash",
        expect_plaintext=False,
    )

    juju.cli("config", application, "--reset", "client-ip-hash-salt")
    # On Juju 4, `juju config --reset` updates the config but does not trigger
    # a config-changed hook, so the charm would keep the old configuration.
    # Touch another option to force a config-changed hook, letting the charm
    # re-render the configuration without the log hash salt.
    juju.config(application, {"global-maxconn": 2048})
    juju.wait(lambda status: all_active_and_idle(status, application))

    # On Juju 4, `juju config` may return before the charm has re-rendered
    # and reloaded haproxy, so the observed log format is polled below.
    restored_client_ip = _request_until_logged(
        juju,
        unit,
        address,
        "restored-plaintext",
        expect_plaintext=True,
    ).rsplit(":", 1)[0]

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

    deadline = time.monotonic() + 300
    hashed_tcp_client = None
    while time.monotonic() < deadline:
        with (
            socket.create_connection((str(haproxy_ip_address), 4444), timeout=30) as sock,
            context.wrap_socket(sock, server_hostname="example.com") as secure_socket,
        ):
            secure_socket.sendall(b"ping")
            assert b"pong" in secure_socket.read()
        field = _last_client_field(juju, unit, "haproxy_route_tcp_4444", required=False)
        if field is not None and not _is_plaintext_address(field):
            hashed_tcp_client = field
            break
        time.sleep(5)
    assert hashed_tcp_client is not None, "no hashed client field found in haproxy TCP logs"
    assert hashed_tcp_client.startswith(f"{expected_hash}:")
    assert not hashed_tcp_client.startswith(f"{restored_client_ip}:")


def _is_plaintext_address(field: str) -> bool:
    """Return whether a logged client field is a plaintext IP:port entry."""
    try:
        ip_address(field.rsplit(":", 1)[0])
    except ValueError:
        return False
    return True


def _request_until_logged(
    juju: jubilant.Juju,
    unit: str,
    address: str,
    marker_prefix: str,
    *,
    expect_plaintext: bool,
    timeout: int = 300,
) -> str:
    """Send requests until the logged client field matches the expectation.

    On Juju 4, `juju config` may return before the charm has re-rendered and
    reloaded haproxy, so a request sent right after a config change can still
    be logged with the previous format. Each attempt uses a fresh marker so
    only the log entry of the latest request is inspected.

    Args:
        juju: Jubilant Juju instance.
        unit: The haproxy unit to read logs from.
        address: The haproxy base URL to send requests to.
        marker_prefix: Prefix of the unique query marker used per attempt.
        expect_plaintext: Whether to wait for a plaintext IP:port field.
        timeout: Seconds to wait before failing.

    Returns:
        The last logged client field matching the expectation.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        marker = f"{marker_prefix}-{uuid.uuid4().hex}"
        response = requests.get(f"{address}/?{marker}", verify=False, timeout=30)  # nosec
        assert response.status_code == 200
        field = _last_client_field(juju, unit, marker, required=False)
        if field is not None and _is_plaintext_address(field) == expect_plaintext:
            return field
        time.sleep(5)
    raise TimeoutError(
        f"no {'plaintext' if expect_plaintext else 'hashed'} client field found"
        f" in haproxy logs within {timeout}s"
    )


def _last_client_field(
    juju: jubilant.Juju, unit: str, marker: str, *, required: bool = True
) -> str | None:
    """Return the client address field (IP:port) of the most recent haproxy access log.

    Logs are read from the journal rather than /var/log/haproxy.log because
    rsyslog file routing does not work in all environments (e.g. nested
    containers), while journald always captures haproxy's syslog output.

    Args:
        juju: Jubilant Juju instance.
        unit: The haproxy unit to read logs from.
        marker: The unique query marker identifying the log entry.
        required: Whether a matching log line must exist.
    """
    logs = juju.exec("journalctl -u haproxy --no-pager -n 50", unit=unit).stdout
    lines = [line for line in logs.splitlines() if " haproxy" in line and marker in line]
    if not lines:
        assert not required, "no haproxy access log lines found"
        return None

    message = lines[-1].split("haproxy", 1)[1].split(None, 1)[1]
    return message.split()[0]
