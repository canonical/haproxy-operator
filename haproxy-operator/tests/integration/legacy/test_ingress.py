# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress relation."""

import ipaddress

import jubilant
import pytest
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG, get_unit_ip_address
from .helper import DNSResolverHTTPSAdapter, get_ingress_url_for_application


@pytest.mark.abort_on_fail
def test_ingress_integration(
    configured_application_with_tls: str,
    any_charm_ingress_requirer: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm with anycharm ingress requirer that installs apache2.
    act: Add the ingress relation.
    assert: The requirer endpoint is available.
    """
    unit_ip_address = get_unit_ip_address(juju, configured_application_with_tls)
    juju.integrate(
        f"{configured_application_with_tls}:ingress",
        f"{any_charm_ingress_requirer}:ingress",
    )
    juju.wait(lambda status: jubilant.all_active(status, configured_application_with_tls))

    ingress_url = get_ingress_url_for_application(juju, any_charm_ingress_requirer)
    model_name = juju.status().model.name
    assert ingress_url.netloc == TEST_EXTERNAL_HOSTNAME_CONFIG
    assert ingress_url.path == f"/{model_name}-{any_charm_ingress_requirer}/"

    session = Session()
    session.mount(
        "https://", DNSResolverHTTPSAdapter(ingress_url.netloc, str(unit_ip_address))
    )

    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        requirer_url = f"http://[{unit_ip_address!s}]{ingress_url.path}ok"
    else:
        requirer_url = f"http://{unit_ip_address!s}{ingress_url.path}ok"

    response = session.get(
        requirer_url,
        headers={"Host": ingress_url.netloc},
        verify=False,  # nosec - calling charm ingress URL
        allow_redirects=False,
        timeout=30,
    )
    assert response.status_code == 302
    assert response.headers["location"] == f"https://{ingress_url.netloc}{ingress_url.path}ok"

    response = session.get(
        requirer_url,
        headers={"Host": ingress_url.netloc},
        verify=False,  # nosec - calling charm ingress URL
        timeout=30,
    )
    assert response.status_code == 200
    assert "ok!" in response.text
