# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy route policy."""

import json
import logging


import jubilant
import pytest

logger = logging.getLogger(__name__)

TEST_HOSTNAME = "example.com"


@pytest.mark.abort_on_fail
def test_haproxy_route_policy(
    configured_application_with_tls: str,
    haproxy_route_policy,
    lxd_juju: jubilant.Juju,
    any_charm_haproxy_route_deployer,
):
    """Test the HAProxy route policy integration."""
    lxd_juju.integrate(
        f"{configured_application_with_tls}:haproxy-route",
        any_charm_haproxy_route_deployer,
    )
    lxd_juju.integrate(
        f"{configured_application_with_tls}:haproxy-route-policy",
        haproxy_route_policy,
    )
    lxd_juju.run(
        f"{any_charm_haproxy_route_deployer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": any_charm_haproxy_route_deployer,
                        "ports": [80],
                        "hostname": TEST_HOSTNAME,
                    }
                ]
            ),
        },
    )
    lxd_juju.wait(jubilant.all_active)
