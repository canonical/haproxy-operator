# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Fixtures for haproxy charm integration tests."""

import json
import logging
import pathlib
import tempfile
import typing
from pathlib import Path

import jubilant
import pytest
import yaml

from .helper import pytestconfig_arg_no_deploy

logger = logging.getLogger(__name__)

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "lib/charms/haproxy/v2/haproxy_route.py"
APT_LIB_SRC = "lib/charms/operator_libs_linux/v0/apt.py"
ANY_CHARM_INGRESS_PER_UNIT_REQUIRER = "ingress-per-unit-requirer-any"
ANY_CHARM_INGRESS_PER_UNIT_REQUIRER_SRC = "tests/integration/ingress_per_unit_requirer.py"
JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
SELF_SIGNED_CERTIFICATES_APP_NAME = "self-signed-certificates"
ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION = "any-charm-haproxy-route-requirer"
HAPROXY_ROUTE_TCP_REQUIRER_SRC = "tests/integration/haproxy_route_tcp_requirer.py"
HAPROXY_ROUTE_TCP_LIB_SRC = "lib/charms/haproxy/v1/haproxy_route_tcp.py"
ANY_CHARM_HAPROXY_ROUTE_TCP_REQUIRER_APPLICATION = "any-charm-haproxy-route-tcp-requirer"
GRPC_SERVER_DIR = pathlib.Path("tests/integration/grpc_server")
GRPC_SERVER_SRC = GRPC_SERVER_DIR / "__main__.py"
GRPC_MESSAGE_STUB_SRC = GRPC_SERVER_DIR / "echo_pb2.py"
GRPC_SERVICE_STUB_SRC = GRPC_SERVER_DIR / "echo_pb2_grpc.py"


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


@pytest.fixture(scope="module", name="configured_application_with_tls_base")
def configured_application_with_tls_base_fixture(
    pytestconfig: pytest.Config,
    application: str,
    certificate_provider_application: str,
    juju: jubilant.Juju,
):
    """The haproxy charm configured and integrated with TLS provider."""
    if pytestconfig.getoption("--no-deploy") and "haproxy" in juju.status().apps:
        return application
    juju.config(application, {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    juju.integrate(
        f"{application}:certificates", f"{certificate_provider_application}:certificates"
    )
    juju.wait(
        lambda status: (
            jubilant.all_active(status, application, certificate_provider_application)
        ),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return application


@pytest.fixture(name="configured_application_with_tls")
def configured_application_with_tls_fixture(
    configured_application_with_tls_base: str,
    certificate_provider_application: str,
    juju: jubilant.Juju,
):
    """Provide haproxy with TLS and clean up test-specific relations after each test.

    This function-scoped fixture wraps the module-scoped configured_application_with_tls_base
    and ensures that relations created during tests are removed, while preserving the
    certificates relation for reuse across tests.
    """
    yield configured_application_with_tls_base

    # Remove all relations except peer relations and the certificates relation
    for endpoint, app_status_relation in (
        juju.status().apps[configured_application_with_tls_base].relations.items()
    ):
        for relation in app_status_relation:
            if relation.related_app == configured_application_with_tls_base:
                continue
            # Keep the certificates relation created by configured_application_with_tls_base fixture
            if (
                endpoint == "certificates"
                and relation.related_app == certificate_provider_application
            ):
                continue
            juju.remove_relation(
                f"{configured_application_with_tls_base}:{endpoint}", relation.related_app
            )
    # Ensure the removal is complete otherwise reintegration in next test may fail
    juju.wait(
        lambda status: (jubilant.all_agents_idle(status)),
    )


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
    return ANY_CHARM_INGRESS_PER_UNIT_REQUIRER


@pytest.fixture(scope="module", name="any_charm_haproxy_route_requirer_base")
@pytestconfig_arg_no_deploy(application=ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION)
def any_charm_haproxy_route_requirer_base_fixture(
    _pytestconfig: pytest.Config, juju: jubilant.Juju
):
    """Deploy any-charm and configure it to serve as a requirer for the haproxy-route
    integration.
    """
    src_overwrite = json.dumps(
        {
            "any_charm.py": pathlib.Path(HAPROXY_ROUTE_REQUIRER_SRC).read_text(encoding="utf-8"),
            "haproxy_route.py": pathlib.Path(HAPROXY_ROUTE_LIB_SRC).read_text(encoding="utf-8"),
            "tls_certificates.py": pathlib.Path(
                "lib/charms/tls_certificates_interface/v4/tls_certificates.py"
            ).read_text(encoding="utf-8"),
            "apt.py": pathlib.Path(APT_LIB_SRC).read_text(encoding="utf-8"),
            "grpc_server/__main__.py": pathlib.Path(GRPC_SERVER_DIR / "__main__.py").read_text(
                encoding="utf-8"
            ),
            "grpc_server/echo_pb2.py": pathlib.Path(GRPC_MESSAGE_STUB_SRC).read_text(
                encoding="utf-8"
            ),
            "grpc_server/echo_pb2_grpc.py": pathlib.Path(GRPC_SERVICE_STUB_SRC).read_text(
                encoding="utf-8"
            ),
        }
    )
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(src_overwrite.encode("utf-8"))
        tf.flush()
        juju.deploy(
            "any-charm",
            app=ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION,
            channel="beta",
            config={
                "src-overwrite": f"@{tf.name}",
                "python-packages": "\n".join(
                    [
                        "pydantic",
                        "cryptography==45.0.6",
                        "grpcio",
                        "grpcio-reflection",
                        "validators",
                    ]
                ),
            },
        )
        juju.wait(
            lambda status: (
                jubilant.all_active(status, ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION)
            ),
            timeout=JUJU_WAIT_TIMEOUT,
        )

    return ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION


@pytest.fixture(name="any_charm_haproxy_route_requirer")
def any_charm_haproxy_route_requirer_fixture(
    any_charm_haproxy_route_requirer_base: str,
    juju: jubilant.Juju,
):
    """Provide haproxy route requirer and clean up test-specific relations after each test.

    This function-scoped fixture wraps the module-scoped any_charm_haproxy_route_requirer_base
    and ensures that relations created during tests are removed, while preserving the
    base application for reuse across tests.
    """
    yield any_charm_haproxy_route_requirer_base

    # Remove all relations except peer relations
    app_name = any_charm_haproxy_route_requirer_base
    if app_name not in juju.status().apps:
        return

    for endpoint, app_status_relation in juju.status().apps[app_name].relations.items():
        for relation in app_status_relation:
            if relation.related_app == app_name:
                continue
            juju.remove_relation(f"{app_name}:{endpoint}", relation.related_app)

    juju.wait(
        lambda status: (jubilant.all_agents_idle(status)),
    )


@pytest.fixture(scope="module", name="any_charm_haproxy_route_tcp_requirer_base")
@pytestconfig_arg_no_deploy(application=ANY_CHARM_HAPROXY_ROUTE_TCP_REQUIRER_APPLICATION)
def any_charm_haproxy_route_tcp_requirer_base_fixture(
    _pytestconfig: pytest.Config, juju: jubilant.Juju
):
    """Deploy any-charm and configure it to serve as a requirer for the haproxy-route
    integration.
    """
    juju.deploy(
        "any-charm",
        app=ANY_CHARM_HAPROXY_ROUTE_TCP_REQUIRER_APPLICATION,
        channel="beta",
        config={
            "src-overwrite": json.dumps(
                {
                    "any_charm.py": pathlib.Path(HAPROXY_ROUTE_TCP_REQUIRER_SRC).read_text(
                        encoding="utf-8"
                    ),
                    "haproxy_route_tcp.py": pathlib.Path(HAPROXY_ROUTE_TCP_LIB_SRC).read_text(
                        encoding="utf-8"
                    ),
                }
            ),
            "python-packages": "pydantic~=2.10\nvalidators",
        },
    )
    juju.wait(
        lambda status: (
            jubilant.all_active(status, ANY_CHARM_HAPROXY_ROUTE_TCP_REQUIRER_APPLICATION)
        ),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return ANY_CHARM_HAPROXY_ROUTE_TCP_REQUIRER_APPLICATION


@pytest.fixture(name="any_charm_haproxy_route_tcp_requirer")
def any_charm_haproxy_route_tcp_requirer_fixture(
    any_charm_haproxy_route_tcp_requirer_base: str,
    juju: jubilant.Juju,
):
    """Provide haproxy route tcp requirer and clean up test-specific relations after each test.

    This function-scoped fixture wraps the module-scoped any_charm_haproxy_route_tcp_requirer_base
    and ensures that relations created during tests are removed, while preserving the
    base application for reuse across tests.
    """
    yield any_charm_haproxy_route_tcp_requirer_base

    # Remove all relations except peer relations
    app_name = any_charm_haproxy_route_tcp_requirer_base
    if app_name not in juju.status().apps:
        return

    for endpoint, app_status_relation in juju.status().apps[app_name].relations.items():
        for relation in app_status_relation:
            if relation.related_app == app_name:
                continue
            juju.remove_relation(f"{app_name}:{endpoint}", relation.related_app)

    juju.wait(
        lambda status: (jubilant.all_agents_idle(status)),
    )
