# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import ipaddress

import jubilant
import pytest
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .helper import (
    DNSResolverHTTPSAdapter,
    get_ingress_per_unit_urls_for_application,
    get_unit_ip_address,
)


@pytest.mark.abort_on_fail
async def test_ingress_per_unit_integration(
    configured_application_with_tls: str,
    any_charm_ingress_per_unit_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    unit_ip = get_unit_ip_address(juju, configured_application_with_tls)
    ingress_urls = get_ingress_per_unit_urls_for_application(
        juju, any_charm_ingress_per_unit_requirer
    )

    for parsed_url in ingress_urls:
        assert parsed_url.netloc == TEST_EXTERNAL_HOSTNAME_CONFIG
        assert parsed_url.scheme == "https"

        path_suffix = f"{parsed_url.path}/ok"

        if isinstance(unit_ip, ipaddress.IPv6Address):
            backend_url = f"http://[{unit_ip}]{path_suffix}"
        else:
            backend_url = f"http://{unit_ip}{path_suffix}"

        session = Session()
        session.mount("https://", DNSResolverHTTPSAdapter(parsed_url.netloc, str(unit_ip)))

        response = session.get(
            backend_url,
            headers={"Host": parsed_url.netloc},
            verify=False,  # nosec
            timeout=30,
        )
        assert response.status_code == 200
        assert "ok!" in response.text
