# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import jubilant
import pytest
import requests

from .conftest import get_unit_address


@pytest.mark.abort_on_fail
def test_deploy(application: str, juju: jubilant.Juju):
    """
    arrange: Deploy the charm.
    act: Send a GET request to the unit's ip address.
    assert: The charm correctly responds with the default page.
    """
    unit_address = get_unit_address(juju, application)
    response = requests.get(unit_address, timeout=5)

    assert "Default page for the haproxy-operator charm" in str(response.content)
