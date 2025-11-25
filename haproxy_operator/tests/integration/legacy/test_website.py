# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the website relation."""

import pytest
import requests
from juju.application import Application

from .conftest import get_unit_address


@pytest.mark.abort_on_fail
async def test_website_relation(
    application: Application,
    reverseproxy_requirer: Application,
):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    await application.model.add_relation(
        f"{application.name}:website", f"{reverseproxy_requirer.name}:reverseproxy"
    )

    await application.model.wait_for_idle(
        apps=[application.name, reverseproxy_requirer.name],
        idle_period=30,
        status="active",
    )

    unit_address = await get_unit_address(reverseproxy_requirer)
    response = requests.get(unit_address, timeout=5)

    assert response.status_code == 200
    assert "Default page for the haproxy-operator charm" in str(response.content)
