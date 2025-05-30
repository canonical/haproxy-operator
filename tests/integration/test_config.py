# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
from juju.application import Application


async def test_config(application: Application):
    """
    arrange: Deploy the charm.
    act: Update the charm config to an invalid value and then a valid value.
    assert: The charm correctly blocks the first time and write the configured
    value to haproxy.cfg the second time.
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
