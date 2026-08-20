# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import hashlib
import time

import jubilant

# Keep in sync with the salt placeholder in src/state/charm_state.py (ISD-6248).
LOG_HASH_SALT = "demo-salt-value"


def test_config(application: str, juju: jubilant.Juju):
    """
    arrange: Deploy the charm.
    act: Update the charm config to an invalid value and then a valid value.
    assert: The charm correctly blocks the first time and writes the configured
    value to haproxy.cfg the second time.
    """
    juju.config(application, {"global-maxconn": "-1"})
    juju.wait(lambda status: status.apps[application].is_blocked)

    juju.config(application, {"global-maxconn": "1024"})
    juju.wait(lambda status: jubilant.all_active(status, application))

    stdout = juju.ssh(f"{application}/0", "cat /etc/haproxy/haproxy.cfg")
    assert "maxconn 1024" in stdout


def _wait_for_haproxy_log_line(
    juju: jubilant.Juju, unit: str, pattern: str, timeout: int = 30
) -> str | None:
    """Poll the unit's haproxy log for a line matching pattern, return the match or None."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        logs = juju.ssh(unit, f"grep '{pattern}' /var/log/haproxy.log || true")
        lines = [line for line in logs.splitlines() if pattern in line]
        if lines:
            return lines[-1]
        time.sleep(2)
    return None


def test_log_hash_client_ip(application: str, juju: jubilant.Juju):
    """
    arrange: Deploy the charm and generate traffic from the unit itself (loopback).
    act: Toggle the log-hash-client-ip config off and on, generating traffic each time.
    assert: With the option disabled, the client IP is logged in plaintext; with
    it enabled, the rendered config overrides log-format/error-log-format and the
    access log contains the salted SHA-256 hash of the client IP instead.
    """
    unit = f"{application}/0"
    # Traffic generated on the unit itself arrives via loopback, so the client
    # IP logged by haproxy is 127.0.0.1 and the expected hash is deterministic.
    client_ip = "127.0.0.1"
    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(client_ip.encode() + LOG_HASH_SALT.encode()).hexdigest().upper()

    juju.config(application, {"log-hash-client-ip": "false"})
    juju.wait(lambda status: jubilant.all_active(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" not in config
    assert "error-log-format" not in config

    juju.ssh(unit, "curl -s --interface 127.0.0.1 http://127.0.0.1/ > /dev/null")
    plaintext_log = _wait_for_haproxy_log_line(juju, unit, "127.0.0.1")
    assert plaintext_log, "expected a plaintext 127.0.0.1 client IP in the access log"
    assert expected_hash not in plaintext_log

    juju.config(application, {"log-hash-client-ip": "true"})
    juju.wait(lambda status: jubilant.all_active(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" in config
    assert "error-log-format" in config
    assert "sha2(256)" in config

    juju.ssh(unit, "curl -s --interface 127.0.0.1 http://127.0.0.1/ > /dev/null")
    hashed_log = _wait_for_haproxy_log_line(juju, unit, expected_hash)
    assert hashed_log, "expected the salted hash of 127.0.0.1 in the access log"
    assert f"{client_ip}:" not in hashed_log

    # The hashed log line must follow HAProxy's default HTTP log format with
    # only the client IP replaced by the hash; compare the entries field by
    # field, skipping the per-request client port and timestamps.
    plaintext_fields = plaintext_log.split("haproxy", 1)[1].split(None, 1)[1].split()
    hashed_fields = hashed_log.split("haproxy", 1)[1].split(None, 1)[1].split()
    assert plaintext_fields[0].startswith(f"{client_ip}:")
    assert hashed_fields[0].startswith(f"{expected_hash}:")
    assert plaintext_fields[2:] == hashed_fields[2:]
