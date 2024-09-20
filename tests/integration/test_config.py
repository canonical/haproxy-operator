# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
from juju.application import Application


async def test_config(application: Application):
    """Deploy the charm, set global-maxconn config and
    verify that the correct value is rendered.
    """
    await application.set_config({"global-maxconn": "-1"})
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=10,
        status="blocked",
    )

    await application.set_config({"global-maxconn": "1024"})
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=10,
        status="active",
    )

    action = await application.units[0].run("cat /etc/haproxy/haproxy.cfg", timeout=60)
    await action.wait()

    code = action.results.get("return-code")
    stdout = action.results.get("stdout")
    assert code == 0
    assert "maxconn 1024" in stdout
