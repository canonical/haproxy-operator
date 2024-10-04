# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import pytest
import requests
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_deploy(application_with_unit_address: tuple[Application, str]):
    """
    arrange: Deploy the charm.
    act: Send a GET request to the unit's ip address.
    assert: The charm correctly response with the default page.
    """
    application, unit_address = application_with_unit_address
    await application.model.wait_for_idle(
        apps=[application.name],
        status="active",
        raise_on_error=True,
    )

    response = requests.get(unit_address, timeout=5)
    assert "Default page for the haproxy-operator charm" in str(response.content)
