# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Integration tests for haproxy charm actions."""


import json

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_get_proxied_endpoints_action(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
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
                        "paths": ["v1", "v2"],
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

    expected_endpoints = json.dumps(
        [
            "https://ok.haproxy.internal/v1",
            "https://ok.haproxy.internal/v2",
            "https://ok2.haproxy.internal/v1",
            "https://ok2.haproxy.internal/v2",
            "https://ok3.haproxy.internal/v1",
            "https://ok3.haproxy.internal/v2",
        ]
    )

    # Test without backend param
    task = juju.run(f"{configured_application_with_tls}/0", "get-proxied-endpoints")

    assert task.results == {"endpoints": expected_endpoints}, task.results

    # Test with backend param
    task = juju.run(
        f"{configured_application_with_tls}/0", "get-proxied-endpoints", {"backend": "any_charm"}
    )

    assert task.results == {"endpoints": expected_endpoints}, task.results

    # Test with backend param with non existing backend
    with pytest.raises(jubilant.TaskError) as excinfo:
        task = juju.run(
            f"{configured_application_with_tls}/0",
            "get-proxied-endpoints",
            {"backend": "other_charm"},
        )
    assert 'No backend with name "other_charm"' in str(excinfo.value)

    juju.remove_relation(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
