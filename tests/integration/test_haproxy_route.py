# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""


import json
import jubilant
import pytest
import time


@pytest.mark.abort_on_fail
async def test_haproxy_route_any_charm_requirer(
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
        {"method": "update_relation",
         "args": json.dumps(
             [
                 {
                     "service": "any_charm_with_retry",
                     "ports": [80],
                     "retry_count": 3,
                     "retry_redispatch" :True,
                     "load_balancing_algorithm": "source",
                     "load_balancing_consistent_hashing" :True,
                     "http_server_close" :True,
                 }
             ]
         )
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
async def test_haproxy_route_protocol_https(
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
        f"{certificate_provider_application}:certificates"
    )
    # give haproxy the ca certificates
    juju.integrate(
        f"{configured_application_with_tls}:receive-ca-certs",
        f"{certificate_provider_application}:send-ca-cert"
    )

    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )

    # Give it some time
    time.sleep(20)
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {"method": "start_ssl_server"}
    )

    # We set the removed retry-interval config option here as
    # ingress-configurator is not yet synced with the updated lib. This will be removed.
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {"method": "update_relation",
         "args": json.dumps(
             [
                 {
                     "service": "any_charm_with_retry",
                     "ports": [80],
                     "retry_count": 3,
                     "retry_redispatch" :True,
                     "load_balancing_algorithm": "source",
                     "load_balancing_consistent_hashing" :True,
                     "http_server_close" :True,
                     "protocol": "https",
                 }
             ]
         )
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
