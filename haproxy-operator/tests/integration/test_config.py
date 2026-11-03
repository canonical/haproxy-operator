# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for client IP log hashing."""

import hashlib

import jubilant
import pytest
import tenacity

from .conftest import LOG_HASH_SALT, all_active_and_idle


def _assert_log_contains(
    juju: jubilant.Juju, unit: str, expected: str, command: str | None = None
) -> None:
    """Assert that the expected string eventually appears in haproxy's journal.

    HAProxy sends logs to journald asynchronously via syslog, and configuration
    changes reload the service in the background. Send the request again on
    every attempt so that it is logged by the reloaded worker, then retry for a
    few seconds to avoid flaky failures.
    """
    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_delay(60),
        wait=tenacity.wait_fixed(2),
        reraise=True,
    ):
        with attempt:
            if command is not None:
                juju.exec(command, unit=unit)
            haproxy_logs = juju.exec("journalctl -u haproxy --no-pager -n 50", unit=unit).stdout
            assert expected in haproxy_logs


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
    juju.config(
        application,
        {"client-ip-hash-salt": str(log_hash_secret)},
    )
    juju.wait(lambda status: all_active_and_idle(status, application))

    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(("127.0.0.1" + LOG_HASH_SALT).encode()).hexdigest().upper()
    _assert_log_contains(juju, unit, expected_hash, "curl -Lk 127.0.0.1")

    request.getfixturevalue("haproxy_route_tcp_plain_tcp_relation")
    # Fix the source port because %cp logs the client port, not the listener port.
    tcp_command = "printf 'ping\\n' | nc -p 45555 127.0.0.1 4444"
    expected_tcp_log = f"{expected_hash}:45555"
    _assert_log_contains(juju, unit, expected_tcp_log, tcp_command)

    nc_result = juju.exec(tcp_command, unit=unit)
    assert "pong" in nc_result.stdout
