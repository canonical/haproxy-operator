# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
import ipaddress

import pytest
import requests
from juju.application import Application
from juju.client._definitions import FullStatus, UnitStatus


@pytest.mark.abort_on_fail
async def test_deploy(application: Application):
    """
    arrange: Deploy the charm.
    act: Send a GET request to the unit's ip address.
    assert: The charm correctly response with the default page.
    """
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

    response = requests.get(url, timeout=5)
    assert "Default page for the haproxy-operator charm" in str(response.content)
