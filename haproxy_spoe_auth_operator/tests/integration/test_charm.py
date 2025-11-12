# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Basic integration tests for the haproxy-spoe-auth charm."""

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_deploy_and_status(application: str, juju: jubilant.Juju):
    """Test charm deployment and basic status.

    Args:
        application: The application name.
        juju: The Juju instance.

    Assert:
        The charm deploys successfully and reaches active status.
    """
    status = juju.status()
    assert application in status["applications"]
    app_status = status["applications"][application]

    # Check that we have at least one unit
    assert len(app_status["units"]) > 0

    # Check the unit status
    unit_name = f"{application}/0"
    unit = app_status["units"][unit_name]
    assert unit["workload-status"]["current"] == "active"


@pytest.mark.abort_on_fail
def test_snap_installed(application: str, juju: jubilant.Juju):
    """Test that the haproxy-spoe-auth snap is installed.

    Args:
        application: The application name.
        juju: The Juju instance.

    Assert:
        The snap is installed on the unit.
    """
    result = juju.ssh(f"{application}/0", "snap list haproxy-spoe-auth")
    assert "haproxy-spoe-auth" in result


@pytest.mark.abort_on_fail
def test_config_file_exists(application: str, juju: jubilant.Juju):
    """Test that the configuration file is created.

    Args:
        application: The application name.
        juju: The Juju instance.

    Assert:
        The config file exists at the expected location.
    """
    result = juju.ssh(
        f"{application}/0",
        "sudo test -f /var/snap/haproxy-spoe-auth/current/config.yaml && echo 'exists'",
    )
    assert "exists" in result
