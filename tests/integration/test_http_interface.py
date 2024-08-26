# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for http interface lib."""

import pytest
import requests
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_http_interface_lib(application: Application, http_requirer: Application):
    """Deploy the charm and integrate it with a http requirer (pollen)

    Assert that the backend service is correctly proxied.
    """
    await application.model.add_relation(application.name, http_requirer.name)
    await application.model.wait_for_idle(
        apps=[http_requirer.name, application.name],
        idle_period=30,
        status="active",
    )
    haproxy_application_status = await application.model.get_status(filters=[application.name])
    haproxy_unit = next(iter(haproxy_application_status.applications[application.name].units))
    haproxy_address = haproxy_application_status["applications"][application.name]["units"][
        haproxy_unit
    ]["address"]

    response = requests.get(f"http://{haproxy_address}", timeout=5)

    assert "Please use the pollinate client." in str(response.content)
    assert response.status_code == 200
