# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Integration tests for haproxy charm actions."""

import json

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_action(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """arrange: Deploy the charm integrated with any_charm haproxy-route.
    act: Trigger the charm's actions (get-proxied-endpoints and get-configuration).
    assert: Each action returns the expected result.
    """
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )

    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm",
                        "ports": [80],
                        "hostname": "ok.haproxy.internal",
                        "additional_hostnames": ["ok2.haproxy.internal", "ok3.haproxy.internal"],
                        "paths": ["/v1", "/v2"],
                    }
                ]
            ),
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )

    # get-proxied-endpoints returns an endpoint for every hostname/path combination.
    expected_endpoints = {
        "https://ok.haproxy.internal/v1",
        "https://ok.haproxy.internal/v2",
        "https://ok2.haproxy.internal/v1",
        "https://ok2.haproxy.internal/v2",
        "https://ok3.haproxy.internal/v1",
        "https://ok3.haproxy.internal/v2",
    }

    # Test without a backend param (filter)
    task = juju.run(f"{configured_application_with_tls}/0", "get-proxied-endpoints")
    endpoints = set(json.loads(task.results["endpoints"]))
    assert endpoints == expected_endpoints, task.results

    # Test with a backend param (filter)
    task = juju.run(
        f"{configured_application_with_tls}/0", "get-proxied-endpoints", {"backend": "any_charm"}
    )
    endpoints = set(json.loads(task.results["endpoints"]))
    assert endpoints == expected_endpoints, task.results

    # Test with a non-existing backend
    task = juju.run(
        f"{configured_application_with_tls}/0",
        "get-proxied-endpoints",
        {"backend": "other_charm"},
    )
    assert task.results == {"endpoints": "[]"}, task.results

    # get-configuration returns exactly the configuration currently on disk.
    on_disk = juju.ssh(f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg")
    task = juju.run(f"{configured_application_with_tls}/0", "get-configuration")
    assert task.results["source"] == "disk", task.results
    assert task.results["configuration"].splitlines() == on_disk.splitlines(), task.results

    juju.remove_relation(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
