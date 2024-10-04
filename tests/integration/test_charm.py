# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
import ipaddress

import pytest
import requests
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_deploy(application: Application, unit_ip_list: list):
    """
    arrange: Deploy the charm.
    act: Send a GET request to the unit's ip address.
    assert: The charm correctly response with the default page.
    """
    await application.model.wait_for_idle(
        apps=[application.name],
        status="active",
        raise_on_error=True,
    )

    assert len(unit_ip_list) > 0
    for unit_ip in unit_ip_list:
        unit_ip_address = ipaddress.ip_address(unit_ip)
        url = f"http://{str(unit_ip_address)}"
        if isinstance(unit_ip_address, ipaddress.IPv6Address):
            url = f"http://[{str(unit_ip_address)}]"

        response = requests.get(url, timeout=5)
        assert "Default page for the haproxy-operator charm" in str(response.content)
