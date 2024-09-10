# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

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

    status: FullStatus = await application.model.get_status([application.name])
    unit_status: UnitStatus = next(iter(status.applications[application.name].units.values()))
    assert unit_status.public_address, "Invalid unit address"
    address = (
        unit_status.public_address
        if isinstance(unit_status.public_address, str)
        else unit_status.public_address.decode()
    )
    response = requests.get(
        (
            f"http://{address}/"
            f"{any_charm_ingress_requirer.model.name}-"
            f"{any_charm_ingress_requirer.name}/ok"
        ),
        timeout=5,
    )
    assert response.status_code == 200
