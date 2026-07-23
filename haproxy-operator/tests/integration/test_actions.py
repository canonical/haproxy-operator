# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Integration tests for haproxy charm actions."""

import json
import time

import jubilant
import pytest


def _integrate_haproxy_route(juju: jubilant.Juju, provider_endpoint: str, requirer: str) -> None:
    """Integrate haproxy-route, retrying while a prior relation is still being removed.

    Tests in this module add and remove the same haproxy-route relation. Because
    relation removal is asynchronous, a subsequent integrate can race with it and
    fail with "already exists"; retry until the previous relation has cleared.

    Args:
        juju: Jubilant juju instance.
        provider_endpoint: The haproxy-route provider endpoint (e.g. "haproxy:haproxy-route").
        requirer: The requirer application name.
    """
    deadline = time.monotonic() + 120
    while True:
        try:
            juju.integrate(provider_endpoint, requirer)
            return
        except jubilant.CLIError as exc:
            if "already exists" in str(exc) and time.monotonic() < deadline:
                time.sleep(2)
                continue
            raise


@pytest.mark.abort_on_fail
def test_get_proxied_endpoints_action(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """arrange: Deploy the charm integrated with any_charm haproxy-route.
    act: Trigger the action 'get-proxied-endpoints.
    assert: The correct proxied endpoints are returned.
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

    expected_endpoints = {
        "https://ok.haproxy.internal/v1",
        "https://ok.haproxy.internal/v2",
        "https://ok2.haproxy.internal/v1",
        "https://ok2.haproxy.internal/v2",
        "https://ok3.haproxy.internal/v1",
        "https://ok3.haproxy.internal/v2",
    }

    # Test without backend param
    task = juju.run(f"{configured_application_with_tls}/0", "get-proxied-endpoints")

    endpoints = set(json.loads(task.results["endpoints"]))
    assert endpoints == expected_endpoints, task.results

    # Test with backend param
    task = juju.run(
        f"{configured_application_with_tls}/0", "get-proxied-endpoints", {"backend": "any_charm"}
    )

    endpoints = set(json.loads(task.results["endpoints"]))
    assert endpoints == expected_endpoints, task.results

    # Test with backend param with non existing backend
    task = juju.run(
        f"{configured_application_with_tls}/0",
        "get-proxied-endpoints",
        {"backend": "other_charm"},
    )
    assert task.results == {"endpoints": "[]"}, task.results

    juju.remove_relation(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )


@pytest.mark.abort_on_fail
def test_get_configuration_action(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """arrange: Deploy the charm integrated with any_charm haproxy-route.
    act: Trigger the action 'get-configuration' in disk and relations modes.
    assert: The returned configuration matches the on-disk haproxy.cfg, and the
        relations-mode preview matches the applied configuration.
    """
    _integrate_haproxy_route(
        juju, f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )

    service_name = "any_charm"
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": service_name,
                        "ports": [80],
                        "hostname": "ok.haproxy.internal",
                        "paths": ["/v1"],
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

    on_disk = juju.ssh(f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg")

    # full=true must return the complete configuration matching what is on disk.
    task = juju.run(f"{configured_application_with_tls}/0", "get-configuration", {"full": True})
    assert task.results["configuration"].splitlines() == on_disk.splitlines(), task.results

    # Recomputing from relations (source=relations) with full=true must match the
    # applied config when the deployment is settled, without touching disk.
    task = juju.run(
        f"{configured_application_with_tls}/0",
        "get-configuration",
        {"source": "relations", "full": True},
    )
    assert task.results["source"] == "relations", task.results
    assert task.results["configuration"].splitlines() == on_disk.splitlines(), task.results

    # Default (full=false) hides the constant scaffold shared with the default
    # render (e.g. the prometheus frontend) but keeps the operator-specific backend.
    task = juju.run(f"{configured_application_with_tls}/0", "get-configuration")
    default_config = task.results["configuration"]
    assert "frontend prometheus" not in default_config, task.results
    assert service_name in default_config, task.results

    # Per-backend filter returns only that backend's own section, section-aware
    # (not grep). Derive a real, non-default backend name from the full config.
    full_config = juju.run(
        f"{configured_application_with_tls}/0", "get-configuration", {"full": True}
    ).results["configuration"]
    backend_names = [
        line.split()[1]
        for line in full_config.splitlines()
        if line.startswith("backend ") and line.split()[1] != "default"
    ]
    assert backend_names, f"expected at least one non-default backend:\n{full_config}"
    target = backend_names[0]
    filtered = juju.run(
        f"{configured_application_with_tls}/0", "get-configuration", {"backend": target}
    ).results["configuration"]
    assert f"backend {target}" in filtered, filtered
    # only the backend section is returned: the frontend and scaffold are excluded
    assert "frontend haproxy" not in filtered, filtered
    assert "frontend prometheus" not in filtered, filtered

    juju.remove_relation(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
