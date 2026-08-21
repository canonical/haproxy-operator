# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import hashlib
import time

import jubilant

from tests.integration.legacy.conftest import all_active_and_idle

# Keep in sync with LOG_SALT_PLACEHOLDER in src/state/charm_state.py (ISD-6248).
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


def _generate_traffic_until_logged(
    juju: jubilant.Juju, unit: str, pattern: str, timeout: int = 60
) -> str | None:
    """Generate loopback HTTP traffic until a matching line appears in the haproxy log.

    Traffic generation is retried inside the poll loop because the unit can
    report active/idle while haproxy is still (re)starting after a config
    change, so a single request may be dropped before the service is ready.
    Logs are read from the journal rather than /var/log/haproxy.log because
    rsyslog file routing does not work in all environments (e.g. nested
    containers), while journald always captures haproxy's syslog output.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        juju.ssh(unit, "curl -s --interface 127.0.0.1 http://127.0.0.1/ > /dev/null || true")
        time.sleep(2)
        logs = juju.ssh(unit, f"journalctl -u haproxy --no-pager | grep '{pattern}' || true")
        lines = [line for line in logs.splitlines() if pattern in line]
        if lines:
            return lines[-1]
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
    juju.wait(lambda status: all_active_and_idle(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" not in config
    assert "error-log-format" not in config

    plaintext_log = _generate_traffic_until_logged(juju, unit, "127.0.0.1")
    assert plaintext_log, "expected a plaintext 127.0.0.1 client IP in the access log"
    assert expected_hash not in plaintext_log

    juju.config(application, {"log-hash-client-ip": "true"})
    juju.wait(lambda status: all_active_and_idle(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" in config
    assert "error-log-format" in config
    assert "sha2(256)" in config

    hashed_log = _generate_traffic_until_logged(juju, unit, expected_hash)
    assert hashed_log, "expected the salted hash of 127.0.0.1 in the access log"
    assert f"{client_ip}:" not in hashed_log

    # The hashed log line must follow HAProxy's default HTTP log format with
    # only the client IP replaced by the hash. The two lines come from separate
    # requests, so per-request values (timers, counters, bytes) can legitimately
    # differ; compare only the stable, format-defining fields and structure.
    # Default httplog fields: client[0] timestamp[1] frontend[2] backend/server[3]
    # timers[4] status[5] bytes[6] cookie[7] cookie[8] termination[9] counters[10]
    # queue[11] request[12:14].
    plaintext_fields = plaintext_log.split("haproxy", 1)[1].split(None, 1)[1].split()
    hashed_fields = hashed_log.split("haproxy", 1)[1].split(None, 1)[1].split()
    assert plaintext_fields[0].startswith(f"{client_ip}:")
    assert hashed_fields[0].startswith(f"{expected_hash}:")
    assert len(plaintext_fields) == len(hashed_fields)
    # frontend name, backend/server, and the request line are stable across requests
    for index in (2, 3, 12, 13, 14):
        assert plaintext_fields[index] == hashed_fields[index]
