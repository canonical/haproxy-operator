# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""


import json
import time

import jubilant
import pytest
import requests

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
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
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
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
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )
    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )
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
def test_haproxy_route_protocol_https(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    # give anycharm a certificate
    juju.integrate(
        f"{any_charm_haproxy_route_requirer}:require-tls-certificates",
        f"{certificate_provider_application}:certificates",
    )

    # Start apache in ssl mode.
    for _ in range(5):
        try:
            juju.run(
                f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "start_ssl_server"}
            )
        except jubilant.TaskError:
            time.sleep(5)
            continue
        break
    else:
        raise AssertionError("Could not start anycharm ssl server")

    # give haproxy the ca certificates
    juju.integrate(
        f"{configured_application_with_tls}:receive-ca-certs",
        f"{certificate_provider_application}:send-ca-cert",
    )

    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
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
                        "ports": [443],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": True,
                        "protocol": "https",
                    }
                ]
            ),
        },
    )

    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        ),
        delay=5,
    )

    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)
    response = requests.get(
        f"https://{haproxy_ip_address}",
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        timeout=5,
        verify=False,  # nosec: B501
    )
    assert response.text == "ok!"
