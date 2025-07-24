# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Fixtures for haproxy charm integration tests."""

import json
import logging
import pathlib
import typing
from pathlib import Path

import jubilant
import pytest
import yaml

logger = logging.getLogger(__name__)

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
GATEWAY_CLASS_CONFIG = "cilium"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "lib/charms/haproxy/v1/haproxy_route.py"
APT_LIB_SRC = "lib/charms/operator_libs_linux/v0/apt.py"
ANY_CHARM_INGRESS_PER_UNIT_REQUIRER = "ingress-per-unit-requirer-any"
ANY_CHARM_INGRESS_PER_UNIT_REQUIRER_SRC = "tests/integration/ingress_per_unit_requirer.py"
JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
SELF_SIGNED_CERTIFICATES_APP_NAME = "self-signed-certificates"


@pytest.fixture(scope="session", name="charm")
def charm_fixture(pytestconfig: pytest.Config):
    """Pytest fixture that packs the charm and returns the filename, or --charm-file if set."""
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    return charm


@pytest.fixture(scope="module", name="juju")
def juju_fixture(request: pytest.FixtureRequest):
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        """Show the debug log if tests failed.

        Args:
            juju: Jubilant juju instance.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju, charm: str):
    """Deploy the haproxy application.

    Args:
        juju: Jubilant juju fixture.
        charm_file: Path to the packed charm file.

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
    return app_name


@pytest.fixture(scope="module", name="certificate_provider_application")
def certificate_provider_application_fixture(
    pytestconfig: pytest.Config,
    juju: jubilant.Juju,
):
    """Deploy self-signed-certificates."""
    if (
        pytestconfig.getoption("--no-deploy")
        and SELF_SIGNED_CERTIFICATES_APP_NAME in juju.status().apps
    ):
        logger.warning("Using existing application: %s", SELF_SIGNED_CERTIFICATES_APP_NAME)
        return SELF_SIGNED_CERTIFICATES_APP_NAME
    juju.deploy(
        "self-signed-certificates", app=SELF_SIGNED_CERTIFICATES_APP_NAME, channel="1/edge"
    )
    return SELF_SIGNED_CERTIFICATES_APP_NAME


@pytest.fixture(scope="module", name="configured_application_with_tls")
def configured_application_with_tls_fixture(
    pytestconfig: pytest.Config,
    application: str,
    certificate_provider_application: str,
    juju: jubilant.Juju,
):
    """The haproxy charm configured and integrated with TLS provider."""
    if pytestconfig.getoption("--no-deploy") and "haproxy" in juju.status().apps:
        return "haproxy"
    juju.config(application, {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    juju.integrate(application, certificate_provider_application)
    juju.wait(
        lambda status: (
            jubilant.all_active(status, application)
            and jubilant.all_active(status, certificate_provider_application)
        ),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return application


@pytest.fixture(name="any_charm_ingress_per_unit_requirer")
def any_charm_ingress_per_unit_requirer_fixture(
    pytestconfig: pytest.Config, juju: jubilant.Juju, configured_application_with_tls: str
) -> str:
    """Deploy any-charm and configure it to serve as a requirer for the ingress-per-unit
    interface.
    """
    if (
        pytestconfig.getoption("--no-deploy")
        and ANY_CHARM_INGRESS_PER_UNIT_REQUIRER in juju.status().apps
    ):
        logger.warning("Using existing application: %s", ANY_CHARM_INGRESS_PER_UNIT_REQUIRER)
        return ANY_CHARM_INGRESS_PER_UNIT_REQUIRER

    any_charm_src_overwrite = {
        "any_charm.py": Path(ANY_CHARM_INGRESS_PER_UNIT_REQUIRER_SRC).read_text(encoding="utf-8"),
        "ingress_per_unit.py": Path("lib/charms/traefik_k8s/v1/ingress_per_unit.py").read_text(
            encoding="utf-8"
        ),
        "apt.py": Path("lib/charms/operator_libs_linux/v0/apt.py").read_text(encoding="utf-8"),
    }

    juju.deploy(
        "any-charm",
        app=ANY_CHARM_INGRESS_PER_UNIT_REQUIRER,
        channel="beta",
        config={
            "src-overwrite": json.dumps(any_charm_src_overwrite),
            "python-packages": "pydantic<2.0",
        },
        num_units=2,
    )

    juju.wait(
        lambda status: (jubilant.all_active(status, ANY_CHARM_INGRESS_PER_UNIT_REQUIRER)),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    juju.integrate(
        f"{configured_application_with_tls}:ingress-per-unit",
        f"{ANY_CHARM_INGRESS_PER_UNIT_REQUIRER}:require-ingress-per-unit",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, ANY_CHARM_INGRESS_PER_UNIT_REQUIRER
        )
    )
    return ANY_CHARM_INGRESS_PER_UNIT_REQUIRER
