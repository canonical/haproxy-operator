# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-route-policy charm integration tests."""

import json
import pathlib

import jubilant
import pytest
import yaml
from opcli.pytest_plugin import CharmPathList

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION = "any-charm-haproxy-route-policy-requirer"
HAPROXY_ROUTE_POLICY_REQUIRER_SRC = "tests/integration/haproxy_route_policy_requirer.py"
HAPROXY_ROUTE_POLICY_LIB_SRC = "lib/charms/haproxy_route_policy/v0/haproxy_route_policy.py"
POSTGRESQL_APPLICATION = "postgresql"


@pytest.fixture(scope="session", name="charm")
def charm_fixture(charm_paths: dict[str, CharmPathList]) -> str:
    """Pytest fixture that returns the path to the haproxy-route-policy charm."""
    return charm_paths["haproxy-route-policy"].path


@pytest.fixture(scope="module", autouse=True)
def _set_juju_timeout(juju: jubilant.Juju) -> None:
    """Set wait_timeout on the juju fixture."""
    juju.wait_timeout = JUJU_WAIT_TIMEOUT


@pytest.fixture(scope="module", name="application")
def application_fixture(juju: jubilant.Juju, charm: str):
    """Deploy the haproxy-route-policy application.

    Args:
        juju: Jubilant juju fixture.
        charm: Path to the packed charm.

    Returns:
        The haproxy-route-policy app name.
    """
    metadata = yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text(encoding="UTF-8"))
    app_name = metadata["name"]
    if app_name in juju.status().apps:
        return app_name
    juju.deploy(
        charm=charm,
        app=app_name,
        base="ubuntu@24.04",
    )
    return app_name


@pytest.fixture(scope="module", name="any_charm_haproxy_route_policy_requirer")
def any_charm_haproxy_route_policy_requirer_fixture(juju: jubilant.Juju):
    """Deploy any-charm and configure it to serve as a requirer for the haproxy-route
    integration.
    """
    if ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION in juju.status().apps:
        return ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION
    juju.deploy(
        "any-charm",
        app=ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION,
        channel="beta",
        config={
            "src-overwrite": json.dumps(
                {
                    "any_charm.py": pathlib.Path(HAPROXY_ROUTE_POLICY_REQUIRER_SRC).read_text(
                        encoding="utf-8"
                    ),
                    "haproxy_route_policy.py": pathlib.Path(
                        HAPROXY_ROUTE_POLICY_LIB_SRC
                    ).read_text(encoding="utf-8"),
                }
            ),
            "python-packages": "pydantic~=2.10\nvalidators",
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION
        ),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION


@pytest.fixture(scope="module", name="postgresql")
def postgresql_fixture(juju: jubilant.Juju):
    """Deploy PostgreSQL."""
    if POSTGRESQL_APPLICATION in juju.status().apps:
        return POSTGRESQL_APPLICATION
    juju.deploy(
        "postgresql",
        app=POSTGRESQL_APPLICATION,
        channel="16/edge",
        base="ubuntu@24.04",
    )
    juju.wait(
        lambda status: jubilant.all_active(status, POSTGRESQL_APPLICATION),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return POSTGRESQL_APPLICATION
