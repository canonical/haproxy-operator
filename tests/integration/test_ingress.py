# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import pytest
import requests
from juju.application import Application

from .conftest import get_unit_address


@pytest.mark.abort_on_fail
async def test_ingress_integration(
    application: Application,
    any_charm_ingress_requirer: Application,
):
    """Deploy the charm with anycharm ingress requirer that installs apache2.

    Assert that the requirer endpoint is available.
    """
    unit_address = await get_unit_address(application)
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
    path = f"{any_charm_ingress_requirer.model.name}-{any_charm_ingress_requirer.name}/ok"
    response = requests.get(f"{unit_address}/{path}", timeout=5)

    assert response.status_code == 200
    assert "ok!" in response.text
