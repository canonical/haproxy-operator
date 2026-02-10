# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Fixtures for haproxy charm integration tests."""

import json
import logging
import pathlib
import subprocess  # nosec
import tempfile
import typing

import jubilant
import pytest
from playwright._impl._driver import compute_driver_executable, get_driver_env

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
SELF_SIGNED_CERTIFICATES_APP_NAME = "self-signed-certificates"
TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "haproxy-operator/lib/charms/haproxy/v2/haproxy_route.py"
APT_LIB_SRC = "haproxy-operator/lib/charms/operator_libs_linux/v0/apt.py"


@pytest.fixture(scope="session", name="lxd_juju")
def lxd_juju_fixture(request: pytest.FixtureRequest):
    """Bootstrap a new lxd controller and model and return a Juju fixture for it."""
    juju = jubilant.Juju()

    lxd_controller_name = "localhost"
    lxd_cloud_name = "localhost"
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    try:
        juju.bootstrap(lxd_cloud_name, lxd_controller_name)
    except jubilant.CLIError as err:
        if not "already exists":
            logger.exception(err)
            raise

    # We need to switch to the controller or commands like add-cloud will not work.
    juju.cli("switch", f"{lxd_controller_name}:", include_model=False)

    model = request.config.getoption("--model")
    if model:
        try:
            juju.add_model(
                model=model, cloud=lxd_cloud_name, controller=lxd_controller_name
            )
        except jubilant.CLIError as err:
            if not "already exists":
                logger.exception(err)
                raise
            juju.model = f"{lxd_controller_name}:{model}"
        juju = jubilant.Juju(model=f"{lxd_controller_name}:{model}")
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        return juju

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(
        keep=keep_models, cloud=lxd_cloud_name, controller=lxd_controller_name
    ) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        return juju


@pytest.fixture(scope="session", name="k8s_juju")
def k8s_juju_fixture(lxd_juju: jubilant.Juju, request: pytest.FixtureRequest):
    """Bootstrap a new k8s model in the lxd controller and return a Juju fixture for it."""
    clouds_json = lxd_juju.cli("clouds", "--format=json", include_model=False)
    clouds = json.loads(clouds_json)
    k8s_clouds = sorted([k for k, v in clouds.items() if v["type"] == "k8s"])
    assert len(k8s_clouds) >= 1, (
        f"At least one cloud of type k8s supported for the test. {k8s_clouds}"
    )
    k8s_cloud = k8s_clouds[0]

    # Add the k8s cloud to our new controller.
    lxd_juju.cli(
        "add-cloud",
        "--controller",
        lxd_juju.status().model.controller,
        k8s_cloud,
        include_model=False,
    )

    new_juju = jubilant.Juju(model=lxd_juju.model)
    new_juju.wait_timeout = JUJU_WAIT_TIMEOUT
    k8s_model_name = f"k{lxd_juju.status().model.name}"
    try:
        new_juju.add_model(k8s_model_name, k8s_cloud)
    except jubilant.CLIError as err:
        if not "already exists":
            logger.exception(err)
            raise
        new_juju.model = k8s_model_name
    yield new_juju


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, lxd_juju: jubilant.Juju):
    """Deploy the haproxy application.

    Args:
        juju: Jubilant juju fixture.
        charm_file: Path to the packed charm file.

    Returns:
        The haproxy app name.
    """
    app_name = "haproxy"
    if pytestconfig.getoption("--no-deploy") and app_name in lxd_juju.status().apps:
        return app_name

    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"{app_name}_" in f), None
    )
    assert charm_file, f"--charm-file with  {app_name} charm should be set"
    lxd_juju.deploy(
        charm=charm_file,
        app=app_name,
        base="ubuntu@24.04",
    )
    return app_name


@pytest.fixture(scope="module", name="ddos_protection_configurator")
def haproxy_ddos_protection_configurator_fixture(
    pytestconfig: pytest.Config, lxd_juju: jubilant.Juju, application: str
):
    """Deploy the haproxy-ddos-protection-configurator application.

    Args:
        pytestconfig: Pytest config to get charm files.
        lxd_juju: Jubilant juju fixture.
        application: The haproxy application name.

    Returns:
        The haproxy-ddos-protection-configurator app name.
    """
    ddos_app_name = "haproxy-ddos-protection-configurator"

    if (
        pytestconfig.getoption("--no-deploy")
        and ddos_app_name in lxd_juju.status().apps
    ):
        return ddos_app_name

    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"{ddos_app_name}_" in f),
        None,
    )
    assert charm_file, f"--charm-file with {ddos_app_name} charm should be set"

    lxd_juju.deploy(
        charm=charm_file,
        app=ddos_app_name,
        base="ubuntu@24.04",
    )

    return ddos_app_name


@pytest.fixture(scope="module", name="configured_application_with_tls_base")
def configured_application_with_tls_base_fixture(
    pytestconfig: pytest.Config,
    application: str,
    certificate_provider_application: str,
    lxd_juju: jubilant.Juju,
):
    """The haproxy charm configured and integrated with TLS provider."""
    if pytestconfig.getoption("--no-deploy") and "haproxy" in lxd_juju.status().apps:
        return application
    lxd_juju.config(application, {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    lxd_juju.integrate(
        f"{application}:certificates",
        f"{certificate_provider_application}:certificates",
    )
    return application


@pytest.fixture(name="configured_application_with_tls")
def configured_application_with_tls_fixture(
    configured_application_with_tls_base: str,
    certificate_provider_application: str,
):
    """Provide haproxy with TLS and clean up test-specific relations after each test.

    This function-scoped fixture wraps the module-scoped configured_application_with_tls_base
    and ensures that relations created during tests are removed, while preserving the
    certificates relation for reuse across tests.
    """
    yield configured_application_with_tls_base


@pytest.fixture(scope="module", name="certificate_provider_application")
def certificate_provider_application_fixture(
    pytestconfig: pytest.Config,
    lxd_juju: jubilant.Juju,
):
    """Deploy self-signed-certificates."""
    if (
        pytestconfig.getoption("--no-deploy")
        and SELF_SIGNED_CERTIFICATES_APP_NAME in lxd_juju.status().apps
    ):
        logger.warning(
            "Using existing application: %s", SELF_SIGNED_CERTIFICATES_APP_NAME
        )
        return SELF_SIGNED_CERTIFICATES_APP_NAME
    lxd_juju.deploy(
        "self-signed-certificates",
        app=SELF_SIGNED_CERTIFICATES_APP_NAME,
        channel="1/edge",
    )
    return SELF_SIGNED_CERTIFICATES_APP_NAME


@pytest.fixture(scope="module", name="iam_bundle")
def deploy_iam_bundle_fixture(k8s_juju: jubilant.Juju):
    """Deploy Canonical identity bundle."""
    # https://github.com/canonical/iam-bundle-integration
    if k8s_juju.status().apps.get("hydra"):
        logger.info("identity-platform is already deployed")
        return
    k8s_juju.deploy(
        "self-signed-certificates", channel="1/stable", revision=317, trust=True
    )
    k8s_juju.deploy("hydra", channel="latest/edge", revision=399, trust=True)
    k8s_juju.deploy("kratos", channel="latest/edge", revision=567, trust=True)
    k8s_juju.deploy(
        "identity-platform-login-ui-operator",
        channel="latest/edge",
        revision=200,
        trust=True,
    )
    k8s_juju.deploy(
        "traefik-k8s",
        "traefik-public",
        channel="latest/edge",
        revision=270,
        trust=True,
    )
    k8s_juju.deploy(
        "postgresql-k8s",
        channel="14/edge",
        base="ubuntu@22.04",
        trust=True,
        config={
            "profile": "testing",
            "plugin_hstore_enable": "true",
            "plugin_pg_trgm_enable": "true",
        },
    )
    # Integrations
    k8s_juju.integrate(
        "hydra:hydra-endpoint-info",
        "identity-platform-login-ui-operator:hydra-endpoint-info",
    )
    k8s_juju.integrate("hydra:hydra-endpoint-info", "kratos:hydra-endpoint-info")
    k8s_juju.integrate(
        "kratos:kratos-info", "identity-platform-login-ui-operator:kratos-info"
    )
    k8s_juju.integrate(
        "hydra:ui-endpoint-info", "identity-platform-login-ui-operator:ui-endpoint-info"
    )
    k8s_juju.integrate(
        "kratos:ui-endpoint-info",
        "identity-platform-login-ui-operator:ui-endpoint-info",
    )
    k8s_juju.integrate("postgresql-k8s:database", "hydra:pg-database")
    k8s_juju.integrate("postgresql-k8s:database", "kratos:pg-database")
    k8s_juju.integrate(
        "self-signed-certificates:certificates", "traefik-public:certificates"
    )
    k8s_juju.integrate("traefik-public:traefik-route", "hydra:public-route")
    k8s_juju.integrate("traefik-public:traefik-route", "kratos:public-route")
    k8s_juju.integrate(
        "traefik-public:traefik-route", "identity-platform-login-ui-operator:public-route"
    )

    k8s_juju.config("kratos", {"enforce_mfa": False})
    k8s_juju.offer(app=f"{k8s_juju.model}.hydra", endpoint="oauth")


@pytest.fixture(scope="module", name="any_charm_haproxy_route_deployer")
def any_charm_haproxy_route_deployer_fixture(
    pytestconfig: pytest.Config,
    lxd_juju: jubilant.Juju,
):
    """Return a fixture function to create haproxy_route requirer anycharms."""

    def deployer(app_name):
        return deploy_any_charm_haproxy_route_requirer(pytestconfig, lxd_juju, app_name)

    yield deployer


def deploy_any_charm_haproxy_route_requirer(
    pytestconfig: pytest.Config, lxd_juju: jubilant.Juju, app_name
):
    """Deploy a haproxy_route requirer anycharm."""
    if pytestconfig.getoption("--no-deploy") and app_name in lxd_juju.status().apps:
        return app_name
    src_overwrite = json.dumps(
        {
            "any_charm.py": pathlib.Path(HAPROXY_ROUTE_REQUIRER_SRC).read_text(
                encoding="utf-8"
            ),
            "haproxy_route.py": pathlib.Path(HAPROXY_ROUTE_LIB_SRC).read_text(
                encoding="utf-8"
            ),
            "apt.py": pathlib.Path(APT_LIB_SRC).read_text(encoding="utf-8"),
        }
    )
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(src_overwrite.encode("utf-8"))
        tf.flush()
        lxd_juju.deploy(
            "any-charm",
            app=app_name,
            channel="beta",
            config={
                "src-overwrite": f"@{tf.name}",
                "python-packages": "pydantic\ncryptography==45.0.6\nvalidators",
            },
        )
    return app_name


@pytest.fixture(scope="module", name="haproxy_spoe_auth_deployer")
def haproxy_spoe_deployer_fixture(
    pytestconfig: pytest.Config,
    lxd_juju: jubilant.Juju,
    application,
    k8s_juju,
    iam_bundle,
):
    """Return a fixture function to deploy haproxy-spoe charms."""

    def deployer(haproxy_spoe_name, hostname):
        haproxy_spoe_name = deploy_spoe_auth(
            pytestconfig, lxd_juju, haproxy_spoe_name, hostname
        )
        k8s_juju.wait(
            lambda status: status.apps["self-signed-certificates"].is_active,
            timeout=5 * 60,
        )
        ca_cert_result = k8s_juju.run(
            "self-signed-certificates/0", "get-ca-certificate"
        )
        ca_cert = ca_cert_result.results["ca-certificate"].encode("utf-8")
        lxd_juju.wait(
            lambda status: not status.apps[haproxy_spoe_name].is_waiting, timeout=5 * 60
        )
        logger.info(lxd_juju.status().apps[haproxy_spoe_name])
        inject_ca_certificate(lxd_juju, f"{haproxy_spoe_name}/0", ca_cert)
        lxd_juju.integrate(f"{k8s_juju.model}.hydra", haproxy_spoe_name)
        lxd_juju.integrate(f"{application}:spoe-auth", haproxy_spoe_name)
        return haproxy_spoe_name

    yield deployer


def deploy_spoe_auth(
    pytestconfig: pytest.Config, lxd_juju: jubilant.Juju, app_name, host_name
) -> str:
    """Deploy the haproxy-spoe-auth charm."""
    charm_name = "haproxy-spoe-auth"
    if pytestconfig.getoption("--no-deploy") and app_name in lxd_juju.status().apps:
        return app_name

    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"{charm_name}_" in f),
        None,
    )
    assert charm_file, f"--charm-file with  {charm_name} charm should be set"

    lxd_juju.deploy(
        charm=charm_file,
        app=app_name,
        config={"hostname": host_name},
    )
    return app_name


def inject_ca_certificate(lxd_juju, unit_name, ca_cert: str):
    """Inject a ca certificate into a juju unit and run update-ca-certificates."""
    juju = lxd_juju
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(ca_cert)
        tf.flush()
        # the unit could be not the number 0.
        juju.scp(tf.name, f"{unit_name}:/home/ubuntu/iam.crt")
        juju.exec(
            command="sudo mv /home/ubuntu/iam.crt /usr/local/share/ca-certificates",
            unit=unit_name,
        )
        juju.exec(command="sudo update-ca-certificates", unit=unit_name)


@pytest.fixture(scope="session")
def browser_context_manager():
    """
    A session-scoped fixture that installs the Playwright browser.
    """
    driver_executable, driver_cli = compute_driver_executable()
    completed_process = subprocess.run(  # nosec
        [driver_executable, driver_cli, "install-deps"], env=get_driver_env()
    )
    logger.info("install-deps output %s", completed_process)
    completed_process = subprocess.run(  # nosec
        [driver_executable, driver_cli, "install", "chromium"], env=get_driver_env()
    )
    logger.info("install chromium %s", completed_process)
