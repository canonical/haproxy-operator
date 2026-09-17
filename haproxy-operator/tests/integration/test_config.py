# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for client IP log hashing."""

import hashlib
import time

import jubilant
import pytest

from .conftest import LOG_HASH_SALT, all_active_and_idle


def test_client_ip_hash_salt(
    configured_application_without_tls: str,
    log_hash_secret_without_tls,
    juju: jubilant.Juju,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy the charm.
    act: Toggle client IP hashing and send HTTP and TCP requests.
    assert: Client IPs are plaintext when disabled and salted hashes when enabled.
    """
    application = configured_application_without_tls
    unit = f"{application}/0"
    juju.config(
        application,
        {"client-ip-hash-salt": str(log_hash_secret_without_tls)},
    )
    juju.wait(lambda status: all_active_and_idle(status, application))
    juju.exec("curl 127.0.0.1", unit=unit)

    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(("127.0.0.1" + LOG_HASH_SALT).encode()).hexdigest().upper()
    haproxy_logs = juju.exec("journalctl -u haproxy --no-pager -n 50", unit=unit).stdout
    assert expected_hash in haproxy_logs

    request.getfixturevalue("haproxy_route_tcp_plain_tcp_relation")
    juju.exec("printf 'ping\\n' | nc 127.0.0.1 4444", unit=unit)

    expected_tcp_log = f"{expected_hash}:4444"
    for _ in range(10):
        haproxy_logs = juju.exec("journalctl -u haproxy --no-pager -n 50", unit=unit).stdout
        if expected_tcp_log in haproxy_logs:
            break
        time.sleep(1)
    else:
        assert expected_tcp_log in haproxy_logs
