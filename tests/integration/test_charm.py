# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import pytest
import requests
from juju.application import Application

from .conftest import get_unit_address


@pytest.mark.abort_on_fail
async def test_deploy(application: Application):
    """
    arrange: Deploy the charm.
    act: Send a GET request to the unit's ip address.
    assert: The charm correctly response with the default page.
    """
    unit_address = await get_unit_address(application)
    response = requests.get(unit_address, timeout=5)

    assert "Default page for the haproxy-operator charm" in str(response.content)
