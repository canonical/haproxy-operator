# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-ddos-protection-configurator charm integration tests."""

import pathlib

import jubilant
import pytest
import yaml
from opcli.pytest_plugin import CharmPathList

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes


@pytest.fixture(scope="session", name="charm")
def charm_fixture(charm_paths: dict[str, CharmPathList]) -> str:
    """Pytest fixture that returns the path to the haproxy-ddos-protection-configurator charm."""
    return charm_paths["haproxy-ddos-protection-configurator"].path


@pytest.fixture(scope="module")
def juju(juju: jubilant.Juju) -> jubilant.Juju:
    """Override juju fixture to set wait_timeout."""
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    return juju


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju, charm: str):
    """Deploy the haproxy-ddos-protection-configurator application.

    Args:
        pytestconfig: Pytest configuration.
        juju: Jubilant juju fixture.
        charm: Path to the packed charm file.

    Returns:
        The haproxy-ddos-protection-configurator app name.
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
    return app_name
