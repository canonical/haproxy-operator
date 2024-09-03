# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import pytest
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_reverseproxy_relation(application: Application, any_charm_requirer: Application):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    await application.model.add_relation(
        f"{application.name}:reverseproxy", any_charm_requirer.name
    )
    action = await any_charm_requirer.units[0].run_action(
        "rpc",
        method="update_relation_data",
    )
    await action.wait()
    await application.model.wait_for_idle(
        apps=[application.name, any_charm_requirer.name],
        idle_period=30,
        status="active",
    )
    action = await any_charm_requirer.units[0].run_action(
        "rpc",
        method="update_relation_data_single_service",
    )
    await action.wait()
    await application.model.wait_for_idle(
        apps=[application.name, any_charm_requirer.name],
        idle_period=30,
        status="active",
    )
