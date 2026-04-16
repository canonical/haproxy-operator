# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-route-policy charm integration tests."""

import json
import pathlib
import typing

import jubilant
import pytest
import yaml

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION = "any-charm-haproxy-route-policy-requirer"
HAPROXY_ROUTE_POLICY_REQUIRER_SRC = "tests/integration/haproxy_route_policy_requirer.py"
HAPROXY_ROUTE_POLICY_LIB_SRC = "lib/charms/haproxy_route_policy/v0/haproxy_route_policy.py"
POSTGRESQL_APPLICATION = "postgresql"


@pytest.fixture(scope="session", name="charm")
def charm_fixture(pytestconfig: pytest.Config):
    """Pytest fixture that returns the --charm-file."""
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    return charm


@pytest.fixture(scope="module", name="juju")
def juju_fixture(request: pytest.FixtureRequest):
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""
    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju, charm: str):
    """Deploy the haproxy-route-policy application.

    Args:
        juju: Jubilant juju fixture.
        charm: Path to the packed charm.

    Returns:
        The haproxy-route-policy app name.
    """
    metadata = yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text(encoding="UTF-8"))
    app_name = metadata["name"]
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        return app_name
    juju.deploy(
        charm=charm,
        app=app_name,
        base="ubuntu@24.04",
        log=False,
    )
    return app_name


@pytest.fixture(scope="module", name="any_charm_haproxy_route_policy_requirer")
def any_charm_haproxy_route_policy_requirer_fixture(
    pytestconfig: pytest.Config, juju: jubilant.Juju
):
    """Deploy any-charm and configure it to serve as a requirer for the haproxy-route
    integration.
    """
    if (
        pytestconfig.getoption("--no-deploy")
        and ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION in juju.status().apps
    ):
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
        log=False,
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION
        ),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return ANY_CHARM_HAPROXY_ROUTE_POLICY_REQUIRER_APPLICATION


@pytest.fixture(scope="module", name="postgresql")
def postgresql_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju):
    """Deploy PostgreSQL."""
    if pytestconfig.getoption("--no-deploy") and POSTGRESQL_APPLICATION in juju.status().apps:
        return POSTGRESQL_APPLICATION
    juju.deploy(
        "postgresql",
        app=POSTGRESQL_APPLICATION,
        channel="16/edge",
        base="ubuntu@24.04",
        log=False,
    )
    juju.wait(
        lambda status: jubilant.all_active(status, POSTGRESQL_APPLICATION),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return POSTGRESQL_APPLICATION
