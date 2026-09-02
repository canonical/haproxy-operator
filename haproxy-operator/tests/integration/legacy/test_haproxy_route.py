# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the haproxy route relation."""

import jubilant
import pytest
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG, get_unit_ip_address
from .helper import DNSResolverHTTPSAdapter

HAPROXY_ROUTE_REQUIRER_HOSTNAME = f"ok.{TEST_EXTERNAL_HOSTNAME_CONFIG}"


@pytest.mark.abort_on_fail
def test_haproxy_route_integration(
    configured_application_with_tls: str,
    haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm with anycharm haproxy-route requirer that installs apache2.
    act: Add the haproxy-route relation and update relation data.
    assert: The requirer endpoint is available.
    """
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route",
        f"{haproxy_route_requirer}:require-haproxy-route",
    )
    juju.run(f"{haproxy_route_requirer}/0", "rpc", {"method": "update_relation"})

    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, haproxy_route_requirer
        )
    )

    unit_ip_address = get_unit_ip_address(juju, configured_application_with_tls)
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
