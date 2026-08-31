# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the http interface."""

import json

import jubilant
import pytest
import requests

from .conftest import get_unit_address, wait_for_relation


@pytest.mark.abort_on_fail
def test_reverseproxy_relation(
    application: str,
    any_charm_requirer: str,
    any_charm_src_invalid_port: dict,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm with valid config.
    act: Add the reverseproxy relation and update relation data.
    assert: Requests are correctly proxied; invalid port causes blocked state.
    """
    juju.run(f"{any_charm_requirer}/0", "rpc", {"method": "start_server"})

    juju.integrate(f"{application}:reverseproxy", any_charm_requirer)
    # On Juju 4 the relation may not be usable by the requirer right after
    # integrate returns, so wait for it before writing relation data.
    wait_for_relation(juju, any_charm_requirer, "provide-http", application)
    juju.run(f"{any_charm_requirer}/0", "rpc", {"method": "update_relation_data"})
    juju.wait(lambda status: jubilant.all_active(status, application, any_charm_requirer))

    unit_address = get_unit_address(juju, application)

    response = requests.get(f"{unit_address}:8994", timeout=5)
    assert response.status_code == 200
    assert "default server healthy" in response.text

    response = requests.get(f"{unit_address}:8994/server1/health", timeout=5)
    assert response.status_code == 200
    assert "server 1 healthy" in response.text

    juju.config(any_charm_requirer, {"src-overwrite": json.dumps(any_charm_src_invalid_port)})
    juju.run(f"{any_charm_requirer}/0", "rpc", {"method": "update_relation_data"})
    juju.wait(lambda status: status.apps[application].is_blocked)
