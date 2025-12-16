# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy-ddos-protection-configurator charm."""

import jubilant
import pytest


@pytest.mark.asyncio
async def test_charm_is_active(juju: jubilant.Juju, application: str):
    """Test that the charm is in active state after deployment.

    Args:
        juju: Jubilant juju fixture.
        application: The deployed application name.
    """
    juju.wait(lambda status: jubilant.all_active(status, application), timeout=600)
