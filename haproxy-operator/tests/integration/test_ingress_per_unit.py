# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import ipaddress

import jubilant
import pytest
import requests

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .helper import (
    get_unit_ip_address,
)


@pytest.mark.abort_on_fail
async def test_ingress_per_unit_integration(
    configured_application_with_tls: str,
    any_charm_ingress_per_unit_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with any-charm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    juju.integrate(
        f"{configured_application_with_tls}:ingress-per-unit",
        f"{any_charm_ingress_per_unit_requirer}:require-ingress-per-unit",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_ingress_per_unit_requirer
        )
    )
    unit_ip = get_unit_ip_address(juju, configured_application_with_tls)
    path = f"{juju.model}-{any_charm_ingress_per_unit_requirer}/0/ok"

    if isinstance(unit_ip, ipaddress.IPv6Address):
        ingress_url = f"https://[{unit_ip}]/{path}"
    else:
        ingress_url = f"https://{unit_ip}/{path}"

    response = requests.get(
        ingress_url,
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        verify=False,  # nosec
        timeout=30,
    )
    assert response.status_code == 200
    assert "ok!" in response.text
