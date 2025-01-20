# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import json

import pytest
import requests
from juju.application import Application

from .conftest import get_unit_address


@pytest.mark.abort_on_fail
async def test_reverseproxy_relation(
    application: Application,
    any_charm_requirer: Application,
    any_charm_src_invalid_port: dict[str, str],
):
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    action = await any_charm_requirer.units[0].run_action(
        "rpc",
        method="start_server",
    )
    await action.wait()

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

    unit_address = await get_unit_address(application)

    response = requests.get(f"{unit_address}:8994", timeout=5)
    assert response.status_code == 200
    assert "default server healthy" in response.text

    response = requests.get(f"{unit_address}:8994/server1/health", timeout=5)
    assert response.status_code == 200
    assert "server 1 healthy" in response.text

    await any_charm_requirer.set_config(
        {"src-overwrite": json.dumps(any_charm_src_invalid_port)},
    )
    action = await any_charm_requirer.units[0].run_action(
        "rpc",
        method="update_relation_data",
    )
    await action.wait()
    await application.model.wait_for_idle(
        apps=[application.name],
        idle_period=30,
        status="blocked",
    )
