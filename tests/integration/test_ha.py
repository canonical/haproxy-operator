# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
import requests
from juju.application import Application

from .conftest import get_unit_ip_address


async def test_ha(application: Application, hacluster: Application):
    """
    arrange: deploy the chrony charm.
    act: request chrony_exporter metrics endpoint.
    assert: confirm that metrics are scraped.
    """
    await application.add_unit(count=3)
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=30,
        status="active",
    )

    await application.model.add_relation(f"{application.name}:ha", f"{hacluster.name}:ha")
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=30,
        status="blocked",
    )

    vip = await get_unit_ip_address(application)
    await application.set_config({"vip": str(vip)})
    await application.model.wait_for_idle(
        apps=[application.name, hacluster.name],
        idle_period=30,
        status="active",
    )
    response = requests.get(url=f"http://{vip}", timeout=30)
    assert "Default page for the haproxy-operator charm" in response.text

    await application.units[0].machine.destroy(force=True)

    response = requests.get(url=f"http://{vip}", timeout=30)
    assert "Default page for the haproxy-operator charm" in response.text
