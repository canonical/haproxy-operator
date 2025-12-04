# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Fixtures for haproxy charm integration tests."""

import logging
import json
import pathlib
import tempfile

import jubilant
import pytest

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
SELF_SIGNED_CERTIFICATES_APP_NAME = "self-signed-certificates"
TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "haproxy-operator/lib/charms/haproxy/v1/haproxy_route.py"
APT_LIB_SRC = "haproxy-operator/lib/charms/operator_libs_linux/v0/apt.py"
TLS_CERTIFICATES_LIB_SRC = "haproxy-operator/lib/charms/tls_certificates_interface/v4/tls_certificates.py"
ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION = "any-charm-haproxy-route-requirer"


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju):
    """Deploy the haproxy application.

    Args:
        juju: Jubilant juju fixture.
        charm_file: Path to the packed charm file.

    Returns:
        The haproxy app name.
    """
    app_name = "haproxy"
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        return app_name

    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"{app_name}_" in f), None
    )
    assert charm_file, f"--charm-file with  {app_name} charm should be set"
    juju.deploy(
        charm=charm_file,
        app=app_name,
        base="ubuntu@24.04",
    )
    return app_name


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
            jubilant.all_active(status, application)
            and jubilant.all_active(status, certificate_provider_application)
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


@pytest.fixture(scope="module", name="any_charm_haproxy_route_requirer")
def any_charm_haproxy_route_requirer_base_fixture(juju: jubilant.Juju):
    """Deploy any-charm and configure it to serve as a requirer for the haproxy-route
    integration.
    """
    src_overwrite = json.dumps(
        {
            "any_charm.py": pathlib.Path(HAPROXY_ROUTE_REQUIRER_SRC).read_text(encoding="utf-8"),
            "haproxy_route.py": pathlib.Path(HAPROXY_ROUTE_LIB_SRC).read_text(encoding="utf-8"),
            "tls_certificates.py": pathlib.Path(TLS_CERTIFICATES_LIB_SRC).read_text(encoding="utf-8"),
            "apt.py": pathlib.Path(APT_LIB_SRC).read_text(encoding="utf-8"),
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
                "python-packages": "pydantic\ncryptography==45.0.6",
            },
        )
    juju.wait(
        lambda status: (jubilant.all_active(status, ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION)),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    juju.run(
        f"{ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION}/0", "rpc", {"method": "start_server"}
    )
    juju.wait(
        lambda status: (jubilant.all_active(status, ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION)),
        timeout=JUJU_WAIT_TIMEOUT,
    )
    return ANY_CHARM_HAPROXY_ROUTE_REQUIRER_APPLICATION



@pytest.fixture(scope="module", name="haproxy_spoe_auth")
def haproxy_spoe_auth_fixture(pytestconfig: pytest.Config, juju: jubilant.Juju):
    """Deploy the haproxy-spoe-auth application.

    Args:
        juju: Jubilant juju fixture.
        charm_file: Path to the packed charm file.

    Returns:
        The haproxy-spoe-auth app name.
    """
    app_name = "haproxy-spoe-auth"
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        return app_name

    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"{app_name}_" in f), None
    )
    assert charm_file, f"--charm-file with  {app_name} charm should be set"

    juju.deploy(
        charm=charm_file,
        app=app_name,
        config={
            "hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
        },
    )
    return app_name


