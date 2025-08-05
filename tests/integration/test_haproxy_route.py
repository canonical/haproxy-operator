# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""


import jubilant
import pytest


@pytest.mark.abort_on_fail
async def test_haproxy_route_ingress_configurator(
    configured_application_with_tls: str,
    ingress_configurator: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    juju.integrate(configured_application_with_tls, ingress_configurator)
    # We set the removed retry-interval config option here as
    # ingress-configurator is not yet synced with the updated lib. This will be removed.
    juju.config(
        ingress_configurator,
        values={"retry-count": 3, "retry-interval": 1, "retry-redispatch": True},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, ingress_configurator
        )
    )
    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/leader", "cat /etc/haproxy/haproxy.cfg"
    )
    assert all(entry in haproxy_config for entry in ["retries 3", "option redispatch"])
    # Integration tests for loadbalacing, cookie and consistent hashing will be added
    # When the ingress-configurator charm is updated with the corresponding charm configs.
