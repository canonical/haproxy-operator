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
    """Deploy the charm with valid config and tls integration.

    Assert on valid output of get-certificate.
    """
    action = await configured_application_with_tls.units[0].run_action(
        "get-certificate", hostname=TEST_EXTERNAL_HOSTNAME_CONFIG
    )
    await action.wait()
    assert action.results
