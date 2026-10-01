# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Basic integration tests for the haproxy-spoe-auth charm."""

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_snap_installed(application: str, juju: jubilant.Juju):
    """Test that the haproxy-spoe-auth snap is installed and its configuration file present.

    Args:
        application: The application name.
        juju: The Juju instance.

    Assert:
        The snap is installed on the unit and the configuration file is present.
    """
    result = juju.exec("snap list haproxy-spoe-auth", unit=f"{application}/0").stdout
    assert "haproxy-spoe-auth" in result
    result = juju.exec(
        "test -f /var/snap/haproxy-spoe-auth/current/config.yaml && echo 'exists'",
        unit=f"{application}/0",
    ).stdout
    assert "exists" in result
