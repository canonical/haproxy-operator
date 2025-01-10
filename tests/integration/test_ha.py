# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
from juju.action import Action
from juju.application import Application

from .conftest import get_unit_ip_address


async def test_ha(application: Application, hacluster: Application):
    """
    arrange: deploy the chrony charm.
    act: request chrony_exporter metrics endpoint.
    assert: confirm that metrics are scraped.
    """
    await application.add_unit(count=2)
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=30,
        status="active",
    )
    vip = await get_unit_ip_address(application)

    await application.set_config({"vip": str(vip)})
    await application.model.add_relation(f"{application.name}:ha", f"{hacluster.name}:ha")
    await application.model.wait_for_idle(
        apps=[application.name, hacluster.name],
        idle_period=30,
        status="active",
    )
    for unit in application.units:
        action: Action = await unit.run("sudo pcs status")
        await action.wait()
        assert "Pacemaker is running" in action.results["stdout"]
