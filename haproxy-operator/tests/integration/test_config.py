# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for client IP log hashing."""

import hashlib

import jubilant
import pytest

from .conftest import LOG_HASH_SALT, all_active_and_idle


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
    juju.exec("curl -Lk 127.0.0.1", unit=unit)

    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(("127.0.0.1" + LOG_HASH_SALT).encode()).hexdigest().upper()
    haproxy_logs = juju.exec("journalctl -u haproxy --no-pager -n 50", unit=unit).stdout
    assert expected_hash in haproxy_logs
