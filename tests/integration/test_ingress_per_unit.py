# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import ipaddress

import pytest
from juju.application import Application
from pytest_operator.plugin import OpsTest
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG, get_unit_ip_address
from .helper import DNSResolverHTTPSAdapter, get_ingress_per_unit_urls_for_application


@pytest.mark.abort_on_fail
async def test_ingress_per_unit_integration(
    configured_application_with_tls: Application,
    any_charm_ingress_per_unit_requirer: Application,
    ops_test: OpsTest,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    application = configured_application_with_tls
    requirer_app = any_charm_ingress_per_unit_requirer
    await configured_application_with_tls.model.add_relation(
        f"{configured_application_with_tls.name}:ingress-per-unit",
        f"{requirer_app.name}:require-ingress-per-unit",
    )
    await configured_application_with_tls.model.wait_for_idle(
        apps=[configured_application_with_tls.name, requirer_app.name],
        idle_period=30,
        status="active",
    )

    unit_ip = await get_unit_ip_address(application)
    ingress_urls = await get_ingress_per_unit_urls_for_application(requirer_app, ops_test)

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
