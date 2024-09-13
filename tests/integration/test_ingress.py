# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import ipaddress

import pytest
import requests
from juju.application import Application
from juju.client._definitions import FullStatus, UnitStatus


@pytest.mark.abort_on_fail
async def test_ingress_integration(
    application: Application, any_charm_ingress_requirer: Application
):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    await application.model.add_relation(
        f"{application.name}:ingress", any_charm_ingress_requirer.name
    )
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=30,
        status="active",
    )
    action = await any_charm_ingress_requirer.units[0].run_action(
        "rpc",
        method="start_server",
    )
    await action.wait()
    status: FullStatus = await application.model.get_status([application.name])
    unit_status: UnitStatus = next(iter(status.applications[application.name].units.values()))
    assert unit_status.public_address, "Invalid unit address"
    address = (
        unit_status.public_address
        if isinstance(unit_status.public_address, str)
        else unit_status.public_address.decode()
    )

    unit_ip_address = ipaddress.ip_address(address)
    url = f"http://{str(unit_ip_address)}"
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        url = f"http://[{str(unit_ip_address)}]"
    path = f"{any_charm_ingress_requirer.model.name}-{any_charm_ingress_requirer.name}/ok"
    response = requests.get(f"{url}/{path}", timeout=5)

    assert response.status_code == 200
