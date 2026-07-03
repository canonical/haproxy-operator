# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test fixtures for haproxy-spoe-auth-operator."""

import logging
import pathlib

import jubilant
import pytest
import yaml
from opcli.pytest_plugin import CharmPathList

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes


@pytest.fixture(scope="session", name="charm")
def charm_fixture(charm_paths: dict[str, CharmPathList]) -> str:
    """Pytest fixture that returns the path to the haproxy-spoe-auth charm."""
    return charm_paths["haproxy-spoe-auth"].path


@pytest.fixture(scope="module", autouse=True)
def _set_juju_timeout(juju: jubilant.Juju) -> None:
    """Set wait_timeout on the juju fixture."""
    juju.wait_timeout = JUJU_WAIT_TIMEOUT


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju, charm: str):
    """Deploy the haproxy application.

    Args:
        pytestconfig: Pytest configuration.
        juju: Jubilant juju fixture.
        charm: Path to the packed charm file.

    Returns:
        The haproxy app name.
    """
    metadata = yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text(encoding="UTF-8"))
    app_name = metadata["name"]
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        return app_name
    juju.deploy(
        charm=charm,
        app=app_name,
        base="ubuntu@24.04",
    )
    juju.wait(
        lambda status: (jubilant.all_blocked(status, app_name)),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return app_name
