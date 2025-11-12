# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test fixtures for haproxy-spoe-auth-operator."""

import pathlib

import jubilant
import pytest


@pytest.fixture(name="juju", scope="module")
def fixture_juju() -> jubilant.Juju:
    """Create a Juju instance for integration testing.

    Returns:
        A Juju instance.
    """
    return jubilant.Juju(model_config={"logging-config": "<root>=INFO"})


@pytest.fixture(name="charm_path", scope="module")
def fixture_charm_path() -> str:
    """Return the path to the charm directory.

    Returns:
        Path to the charm directory.
    """
    return str(pathlib.Path(__file__).parent.parent.parent)


@pytest.fixture(name="application", scope="module")
def fixture_application(juju: jubilant.Juju, charm_path: str) -> str:
    """Deploy the haproxy-spoe-auth charm.

    Args:
        juju: The Juju instance.
        charm_path: Path to the charm.

    Returns:
        The application name.
    """
    app_name = "haproxy-spoe-auth"
    juju.deploy(charm_path, app_name)
    juju.wait(lambda status: jubilant.all_active(status, app_name))
    return app_name
