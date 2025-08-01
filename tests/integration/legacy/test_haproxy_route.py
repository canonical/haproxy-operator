# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the haproxy route relation."""

import pytest
from juju.application import Application
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG, get_unit_ip_address
from .helper import DNSResolverHTTPSAdapter

HAPROXY_ROUTE_REQUIRER_HOSTNAME = f"ok.{TEST_EXTERNAL_HOSTNAME_CONFIG}"


@pytest.mark.abort_on_fail
async def test_haproxy_route_integration(
    configured_application_with_tls: Application,
    haproxy_route_requirer: Application,
):
    """Deploy the charm with anycharm haproxy-route requirer that installs apache2.

    Assert that the requirer endpoint is available.
    """
    application = configured_application_with_tls

    await application.model.add_relation(
        f"{application.name}:haproxy-route", f"{haproxy_route_requirer.name}:require-haproxy-route"
    )
    action = await haproxy_route_requirer.units[0].run_action("rpc", method="update_relation")
    await action.wait()

    await application.model.wait_for_idle(
        apps=[application.name, haproxy_route_requirer.name],
        idle_period=30,
        status="active",
    )

    unit_ip_address = await get_unit_ip_address(application)
    session = Session()
    for subdomain in ["ok", "ok2", "ok3"]:
        url = f"https://{subdomain}.{TEST_EXTERNAL_HOSTNAME_CONFIG}"
        session.mount(
            url,
            DNSResolverHTTPSAdapter(
                f"{subdomain}.{TEST_EXTERNAL_HOSTNAME_CONFIG}", str(unit_ip_address)
            ),
        )
        response = session.get(
            url,
            verify=False,  # nosec - calling charm ingress URL
            timeout=30,
        )
        assert response.status_code == 200
        assert "ok!" in response.text
