# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
from juju.application import Application
from pytest_operator.plugin import OpsTest


async def test_metrics(application: Application, ops_test: OpsTest):
    """
    arrange: deploy the chrony charm.
    act: request chrony_exporter metrics endpoint.
    assert: confirm that metrics are scraped.
    """
    for unit in application.units:
        _, stdout, _ = await ops_test.juju(
            "ssh", unit.name, "curl", "-m", "10", "localhost:9123/metrics"
        )
        assert "haproxy_backend_max_connect_time_seconds" in stdout
