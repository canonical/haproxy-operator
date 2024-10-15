# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import pytest
from juju.application import Application

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.abort_on_fail
async def test_get_certificate_action(
    configured_application_with_tls: Application,
):
    """
    arrange: Deploy the charm with valid config and tls integration.
    act: Run the get-certificate action and run a sh command to check
    the cert location on the unit.
    assert: The output of both operations are valid.
    """
    action = await configured_application_with_tls.units[0].run_action(
        "get-certificate", hostname=TEST_EXTERNAL_HOSTNAME_CONFIG
    )
    await action.wait()
    assert "-----BEGIN CERTIFICATE-----" in action.results.get("certificate")

    action = await configured_application_with_tls.units[0].run(
        "ls /var/lib/haproxy/certs", timeout=60
    )
    await action.wait()

    stdout = action.results.get("stdout")
    assert f"{TEST_EXTERNAL_HOSTNAME_CONFIG}.pem" in stdout


@pytest.mark.abort_on_fail
async def test_get_certificate_action_missing_param(
    configured_application_with_tls: Application,
):
    """
    arrange: Deploy the charm with valid config and tls integration.
    act: Run the get-certificate action without the required hostname parameter.
    assert: The action fails.
    """
    with pytest.raises(Exception):
        action = await configured_application_with_tls.units[0].run_action("get-certificate")
        await action.wait()
