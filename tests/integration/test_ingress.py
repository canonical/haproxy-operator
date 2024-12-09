# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import ipaddress

import pytest
from juju.application import Application
from pytest_operator.plugin import OpsTest
from requests import Session

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG, get_unit_ip_address
from .helper import DNSResolverHTTPSAdapter, get_ingress_url_for_application


@pytest.mark.abort_on_fail
async def test_ingress_integration(
    configured_application_with_tls: Application,
    any_charm_ingress_requirer: Application,
    ops_test: OpsTest,
):
    """Deploy the charm with anycharm ingress requirer that installs apache2.

    Assert that the requirer endpoint is available.
    """
    application = configured_application_with_tls
    unit_ip_address = await get_unit_ip_address(application)
    action = await any_charm_ingress_requirer.units[0].run_action(
        "rpc",
        method="start_server",
    )
    await action.wait()
    await application.model.add_relation(
        f"{application.name}:ingress", any_charm_ingress_requirer.name
    )
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=30,
        status="active",
    )

    ingress_url = await get_ingress_url_for_application(any_charm_ingress_requirer, ops_test)
    assert ingress_url.netloc == TEST_EXTERNAL_HOSTNAME_CONFIG
    assert ingress_url.path == f"/{application.model.name}-{any_charm_ingress_requirer.name}/"

    session = Session()
    session.mount("https://", DNSResolverHTTPSAdapter(ingress_url.netloc, str(unit_ip_address)))

    requirer_url = f"http://{str(unit_ip_address)}/{ingress_url.path}ok"
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        requirer_url = f"http://[{str(unit_ip_address)}]/{ingress_url.path}ok"
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
