# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import jubilant


def test_metrics(application: str, juju: jubilant.Juju):
    """
    arrange: deploy the haproxy charm.
    act: request haproxy metrics endpoint via SSH.
    assert: confirm that metrics are available.
    """
    stdout = juju.ssh(f"{application}/0", "curl -m 10 localhost:8404/metrics")
    assert "haproxy_backend_max_connect_time_seconds" in stdout
