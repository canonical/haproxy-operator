# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the HAProxy workload version."""

import jubilant

from .conftest import all_active_and_idle


def test_haproxy_version(application: str, juju: jubilant.Juju):
    """
    arrange: Deploy the charm.
    act: Read the installed HAProxy version.
    assert: The installed HAProxy version is 3.2.
    """
    juju.wait(lambda status: all_active_and_idle(status, application))

    result = juju.exec("haproxy -v 2>&1", unit=f"{application}/0")

    assert "version 3.2" in result.stdout
