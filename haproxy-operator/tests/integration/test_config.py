# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for client IP log hashing."""

import hashlib

import jubilant
import pytest
import tenacity

from .conftest import LOG_HASH_SALT, all_active_and_idle


def _assert_log_contains(juju: jubilant.Juju, unit: str, expected: str) -> None:
    """Assert that the expected string eventually appears in haproxy's journal.

    HAProxy sends logs to journald asynchronously via syslog, so the log line
    for a request may not be visible immediately after the request completes.
    Retry for a few seconds to avoid flaky failures.
    """
    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_delay(30),
        wait=tenacity.wait_fixed(2),
        reraise=True,
    ):
        with attempt:
            haproxy_logs = juju.exec("journalctl -u haproxy --no-pager -n 50", unit=unit).stdout
            assert expected in haproxy_logs


def _wait_for_config_contains(juju: jubilant.Juju, unit: str, expected: str) -> None:
    """Wait until the rendered haproxy configuration on disk contains the expected string.

    Juju can report a unit as active and idle before it processes the pending
    configuration change, so wait for the new configuration to be rendered
    before sending requests.
    """
    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_delay(30),
        wait=tenacity.wait_fixed(1),
        reraise=True,
    ):
        with attempt:
            configuration = juju.exec("cat /etc/haproxy/haproxy.cfg", unit=unit).stdout
            assert expected in configuration


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
    # Wait for the new configuration before sending requests: the unit can be
    # reported as idle while the configuration change is still pending.
    _wait_for_config_contains(juju, unit, LOG_HASH_SALT)
    juju.wait(lambda status: all_active_and_idle(status, application))

    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(("127.0.0.1" + LOG_HASH_SALT).encode()).hexdigest().upper()
    juju.exec("curl -Lk 127.0.0.1", unit=unit)
    _assert_log_contains(juju, unit, expected_hash)

    request.getfixturevalue("haproxy_route_tcp_plain_tcp_relation")
    # Fix the source port because %cp logs the client port, not the listener port.
    nc_result = juju.exec("printf 'ping\\n' | nc -p 45555 127.0.0.1 4444", unit=unit)
    assert "pong" in nc_result.stdout

    expected_tcp_log = f"{expected_hash}:45555"
    _assert_log_contains(juju, unit, expected_tcp_log)
