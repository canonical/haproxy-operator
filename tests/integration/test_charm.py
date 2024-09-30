# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
import pytest
import requests
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_deploy(application: Application):
    """
    arrange: Deploy the charm.
    act: Send a GET request to the unit's ip address.
    assert: The charm correctly response with the default page.
    """
    status = await application.model.get_status(filters=[application.name])
    unit = next(iter(status.applications[application.name].units))
    unit_address = status["applications"][application.name]["units"][unit]["address"]
    assert unit_address

    response = requests.get(
        f"http://{unit_address}",
        timeout=5,
    )
    assert "Default page for the haproxy-operator charm" in str(response.content)
