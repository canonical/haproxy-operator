# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import json

import httpx
import jubilant
import pytest

from .conftest import all_active_and_idle
from .helper import get_unit_ip_address


@pytest.mark.abort_on_fail
def test_haproxy_route_any_charm_requirer(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    juju.run(f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "start_server"})

    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
    juju.wait(
        lambda status: (
            jubilant.all_blocked(status, configured_application_with_tls)
            and jubilant.all_agents_idle(
                status, configured_application_with_tls, any_charm_haproxy_route_requirer
            )
        ),
    )
    # We set the removed retry-interval config option here as
    # ingress-configurator is not yet synced with the updated lib. This will be removed.
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [80],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": True,
                    }
                ]
            ),
        },
    )
    juju.wait(
        lambda status: all_active_and_idle(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )
    haproxy_config = juju.exec(
        "cat /etc/haproxy/haproxy.cfg", unit=f"{configured_application_with_tls}/0"
    ).stdout
    assert all(
        entry in haproxy_config
        for entry in [
            "retries 3",
            "option redispatch",
            "option http-server-close",
            "balance source",
            "hash-type consistent",
        ]
    )


@pytest.mark.abort_on_fail
def test_haproxy_route_default_backend(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Mark the requirer as the default backend and assert that it is used as the target of
    the default_backend directive, renders no ACL, and serves requests that do not match
    any configured hostname.
    """
    juju.run(f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "start_server"})

    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
    juju.wait(
        lambda status: (
            jubilant.all_blocked(status, configured_application_with_tls)
            and jubilant.all_agents_idle(
                status, configured_application_with_tls, any_charm_haproxy_route_requirer
            )
        ),
    )
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_default_backend",
                        "ports": [80],
                        "default_backend": True,
                    }
                ]
            ),
        },
    )
    juju.wait(
        lambda status: all_active_and_idle(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )
    haproxy_config = juju.exec(
        "cat /etc/haproxy/haproxy.cfg", unit=f"{configured_application_with_tls}/0"
    ).stdout
    assert "default_backend default\n" not in haproxy_config
    assert "backend default\n" not in haproxy_config
    assert "default_backend any_charm_default_backend\n" in haproxy_config
    assert "use_backend any_charm_default_backend" not in haproxy_config
    assert "acl_host_any_charm_default_backend" not in haproxy_config

    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)
    with httpx.Client(http2=False, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={"Host": "does-not-match.example.com"},
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert "ok!" in response.text
