# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for the log-hash-client-ip config option."""

import hashlib

import jubilant
import requests

from .conftest import all_active_and_idle
from .helper import get_unit_address

# Keep in sync with LOG_SALT_PLACEHOLDER in src/state/log_formats.py (ISD-6248).
LOG_HASH_SALT = "demo-salt-value"


def _last_client_field(juju: jubilant.Juju, unit: str) -> str:
    """Return the client address field (IP:port) of the most recent haproxy access log.

    Logs are read from the journal rather than /var/log/haproxy.log because
    rsyslog file routing does not work in all environments (e.g. nested
    containers), while journald always captures haproxy's syslog output.
    """
    logs = juju.ssh(unit, "journalctl -u haproxy --no-pager -n 50")
    lines = [line for line in logs.splitlines() if " haproxy" in line and "GET" in line]
    assert lines, "no haproxy access log lines found"

    message = lines[-1].split("haproxy", 1)[1].split(None, 1)[1]
    return message.split()[0]


def test_log_hash_client_ip(application: str, juju: jubilant.Juju):
    """
    arrange: Deploy the charm.
    act: Toggle the log-hash-client-ip config off and on, sending an HTTP
    request each time.
    assert: With the option disabled, the access log shows the client IP in
    plaintext; with it enabled, the rendered config overrides
    log-format/error-log-format and the access log shows the salted SHA-256 hash
    of that same client IP.
    """
    unit = f"{application}/0"
    juju.wait(lambda status: all_active_and_idle(status, application))
    address = get_unit_address(juju, application)

    juju.config(application, {"log-hash-client-ip": "false"})
    juju.wait(lambda status: all_active_and_idle(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" not in config
    assert "error-log-format" not in config

    requests.get(f"{address}/", timeout=10)
    client_ip = _last_client_field(juju, unit).rsplit(":", 1)[0]
    assert client_ip, "expected a plaintext client IP in the access log"

    juju.config(application, {"log-hash-client-ip": "true"})
    juju.wait(lambda status: all_active_and_idle(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" in config
    assert "error-log-format" in config
    assert "sha2(256)" in config

    # HAProxy's hex converter outputs uppercase.
    expected_hash = hashlib.sha256(client_ip.encode() + LOG_HASH_SALT.encode()).hexdigest().upper()
    requests.get(f"{address}/", timeout=10)
    hashed_client = _last_client_field(juju, unit)
    assert hashed_client.startswith(f"{expected_hash}:")
    assert not hashed_client.startswith(f"{client_ip}:")
