# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy route policy."""

import logging


import jubilant
import pytest
from typing import Callable, Any
import json
import requests
from .helper import get_unit_ip_address

logger = logging.getLogger(__name__)

TEST_HOSTNAME = "example.com"
HAPROXY_ROUTE_REQUIRER_NAME = "haproxy-route-requirer"


@pytest.mark.abort_on_fail
def test_haproxy_route_policy(
    configured_application_with_tls: str,
    haproxy_route_policy: str,
    lxd_juju: jubilant.Juju,
    postgresql: str,
    any_charm_haproxy_route_deployer: Callable[[str], Any],
):
    """Test the HAProxy route policy integration."""
    lxd_juju.config(
        configured_application_with_tls, {"external-hostname": TEST_HOSTNAME}
    )
    any_charm_haproxy_route_deployer(HAPROXY_ROUTE_REQUIRER_NAME)
    lxd_juju.integrate(f"{haproxy_route_policy}:database", f"{postgresql}:database")
    lxd_juju.integrate(
        f"{configured_application_with_tls}:haproxy-route-policy",
        haproxy_route_policy,
    )
    lxd_juju.integrate(
        f"{HAPROXY_ROUTE_REQUIRER_NAME}:require-haproxy-route",
        configured_application_with_tls,
    )
    # Wait for any-charm to settle before running the action
    lxd_juju.wait(
        lambda status: not status.apps[HAPROXY_ROUTE_REQUIRER_NAME].is_waiting,
        timeout=5 * 60,
    )
    lxd_juju.run(
        f"{HAPROXY_ROUTE_REQUIRER_NAME}/leader",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": HAPROXY_ROUTE_REQUIRER_NAME,
                        "ports": [80],
                        "hostname": TEST_HOSTNAME,
                    }
                ]
            ),
        },
    )
    lxd_juju.wait(jubilant.all_active)
    admin_credentials = lxd_juju.run(
        f"{haproxy_route_policy}/leader",
        "get-admin-credentials",
    )
    haproxy_unit_ip = get_unit_ip_address(lxd_juju, configured_application_with_tls)
    response = requests.get(
        f"https://{str(haproxy_unit_ip)}/api/v1/requests",
        headers={
            "Host": f"{lxd_juju.model.split(':')[1]}-{haproxy_route_policy}.{TEST_HOSTNAME}"
        },
        auth=("admin", admin_credentials.results["password"]),
        verify=False,
    )
    backend_requests = response.json()
    assert len(backend_requests) == 1
    assert backend_requests[0]["hostname_acls"] == [TEST_HOSTNAME]
    assert backend_requests[0]["status"] == "pending"
