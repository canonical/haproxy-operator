# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy-ddos-protection-configurator charm."""

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_charm_is_active(juju: jubilant.Juju, application: str):
    """Test that the charm is in active state after deployment.

    arrange: charm is deployed.
    act: wait for the charm to become active.
    assert: the charm is in active state.
    """
    juju.wait(lambda status: jubilant.all_active(status, application), timeout=10 * 60)
