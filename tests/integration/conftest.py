# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Fixtures for haproxy charm integration tests."""

import logging
import json
import pathlib
import tempfile
import typing
import subprocess  # nosec

import jubilant
import pytest
from playwright._impl._driver import compute_driver_executable, get_driver_env

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes
SELF_SIGNED_CERTIFICATES_APP_NAME = "self-signed-certificates"
TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "haproxy-operator/lib/charms/haproxy/v1/haproxy_route.py"
APT_LIB_SRC = "haproxy-operator/lib/charms/operator_libs_linux/v0/apt.py"


@pytest.fixture(scope="session", name="lxd_controller")
def lxd_controller_fixture(request: pytest.FixtureRequest) -> str:
    """TODO BOOTSTRAP A CONTROLLER IN LXD, AND ADDS A CLOUD FROM K8S!"""
    juju = jubilant.Juju()
    lxd_controller_name = "localhost"
    lxd_cloud_name = "localhost"
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    try:
        juju.bootstrap(lxd_cloud_name, lxd_controller_name)
    except jubilant.CLIError as err:
        logger.exception(err)
        if "already exists" not in err.stderr:
            raise
    return lxd_controller_name


@pytest.fixture(scope="session", name="lxd_juju")
def lxd_juju_fixture(request: pytest.FixtureRequest, lxd_controller):
    juju = jubilant.Juju()

    lxd_cloud_name = "localhost"
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    try:
        juju.bootstrap(lxd_cloud_name, lxd_controller)
    except jubilant.CLIError as err:
        if not "already exists":
            logger.exception(err)
            raise

    # we need to switch or commands like add-cloud do not work.
    juju.cli("switch", f"{lxd_controller}:", include_model=False)

    model = request.config.getoption("--model")
    if model:
        try:
            juju.add_model(model=model, cloud=lxd_cloud_name, controller=lxd_controller)
        except jubilant.CLIError as err:
            if not "already exists":
                logger.exception(err)
                raise
            juju.model = f"{lxd_controller}:{model}"
        juju = jubilant.Juju(model=f"{lxd_controller}:{model}")
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(
        keep=keep_models, cloud=lxd_cloud_name, controller=lxd_controller
    ) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju


@pytest.fixture(scope="session", name="k8s_juju")
def k8s_juju_fixture(request: pytest.FixtureRequest, lxd_juju):
    # For this, we are using the controller in a k8s cloud. That we suppose it exists and that
    # the name contains k8s.
    
    juju = jubilant.Juju()
    controllers_json = juju.cli(
        "controllers", "--format=json", include_model=False
    )
    controllers = json.loads(controllers_json)
    controllers = controllers["controllers"]
    k8s_controllers = sorted([name for name in controllers.keys() if "k8s" in name])
    assert len(k8s_controllers) == 1, f"Only one controller of type k8s supported for the test. {k8s_controllers}"
    k8s_controller = k8s_controllers[0]

    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    k8s_model_name = lxd_juju.model.split(":")[-1]
    try:
        juju.add_model(model=k8s_model_name, controller=k8s_controller)
    except jubilant.CLIError as err:
        logger.exception(err)
        if not "already exists":
            raise
        juju.model = f"{k8s_controller}:{k8s_model_name}"
    yield juju


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


@pytest.fixture(scope="module", name="iam_bundle")
def deploy_iam_bundle_fixture(k8s_juju: jubilant.Juju):
    """Deploy Canonical identity bundle."""
    # https://github.com/canonical/iam-bundle-integration
    juju = k8s_juju
    if juju.status().apps.get("hydra"):
        logger.info("identity-platform is already deployed")
        return
    juju.deploy("self-signed-certificates", channel="latest/stable", revision=155, trust=True)
    juju.deploy("hydra", channel="latest/stable", revision=362, trust=True)
    juju.deploy("kratos", channel="latest/stable", revision=527, trust=True)
    juju.deploy(
        "identity-platform-login-ui-operator", channel="latest/stable", revision=166, trust=True
    )
    juju.deploy("traefik-k8s", "traefik-admin", channel="latest/stable", revision=176, trust=True)
    juju.deploy("traefik-k8s", "traefik-public", channel="latest/stable", revision=176, trust=True)
    juju.deploy(
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
    juju.integrate(
        "hydra:hydra-endpoint-info", "identity-platform-login-ui-operator:hydra-endpoint-info"
    )
    juju.integrate("hydra:hydra-endpoint-info", "kratos:hydra-endpoint-info")
    juju.integrate("kratos:kratos-info", "identity-platform-login-ui-operator:kratos-info")
    juju.integrate(
        "hydra:ui-endpoint-info", "identity-platform-login-ui-operator:ui-endpoint-info"
    )
    juju.integrate(
        "kratos:ui-endpoint-info", "identity-platform-login-ui-operator:ui-endpoint-info"
    )
    juju.integrate("postgresql-k8s:database", "hydra:pg-database")
    juju.integrate("postgresql-k8s:database", "kratos:pg-database")
    juju.integrate("self-signed-certificates:certificates", "traefik-admin:certificates")
    juju.integrate("self-signed-certificates:certificates", "traefik-public:certificates")
    juju.integrate("traefik-admin:ingress", "hydra:admin-ingress")
    juju.integrate("traefik-admin:ingress", "kratos:admin-ingress")
    juju.integrate("traefik-public:ingress", "hydra:public-ingress")
    juju.integrate("traefik-public:ingress", "kratos:public-ingress")
    juju.integrate("traefik-public:ingress", "identity-platform-login-ui-operator:ingress")

    juju.config("kratos", {"enforce_mfa": False})
    juju_controller, juju_model = juju.model.split(":")
    juju.offer(app=f"{juju_model}.hydra", controller=juju_controller, endpoint="oauth")


@pytest.fixture(scope="module", name="any_charm_haproxy_route_deployer")
def any_charm_haproxy_route_deployer_fixture(
        lxd_juju: jubilant.Juju,
):
    def deployer(app_name):
        return deploy_any_charm_haproxy_route_requirer(juju, app_name)

    yield deployer


def deploy_any_charm_haproxy_route_requirer(juju: jubilant.Juju, app_name):
    src_overwrite = json.dumps(
        {
            "any_charm.py": pathlib.Path(HAPROXY_ROUTE_REQUIRER_SRC).read_text(encoding="utf-8"),
            "haproxy_route.py": pathlib.Path(HAPROXY_ROUTE_LIB_SRC).read_text(encoding="utf-8"),
            "apt.py": pathlib.Path(APT_LIB_SRC).read_text(encoding="utf-8"),
        }
    )
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(src_overwrite.encode("utf-8"))
        tf.flush()
        juju.deploy(
            "any-charm",
            app=app_name,
            channel="beta",
            config={
                "src-overwrite": f"@{tf.name}",
                "python-packages": "pydantic\ncryptography==45.0.6",
            },
        )
    return app_name


@pytest.fixture(scope="module", name="haproxy_spoe_auth_deployer")
def haproxy_spoe_deployer_fixture(
        pytestconfig: pytest.Config,
        juju: jubilant.Juju,
        application,
        k8s_juju,
        iam_bundle
):
    def deployer(haproxy_spoe_name, hostname):
        haproxy_spoe_name = deploy_spoe_auth(pytestconfig, juju, haproxy_spoe_name, hostname)
        k8s_juju.wait(lambda status: status.apps["self-signed-certificates"].is_active, timeout=5 * 60)
        ca_cert_result = k8s_juju.run("self-signed-certificates/0", "get-ca-certificate")
        ca_cert = ca_cert_result.results["ca-certificate"].encode("utf-8")
        # I think app waiting could have unit allocating.
        juju.wait(lambda status: not status.apps[haproxy_spoe_name].is_waiting, timeout=5 * 60)
        logger.info(juju.status().apps[haproxy_spoe_name])
        # Why unit 0?
        inject_ca_certificate(juju, f"{haproxy_spoe_name}/0", ca_cert)
        juju.integrate(f"{k8s_juju.model}.hydra", haproxy_spoe_name)
        juju.integrate(f"{application}:spoe-auth", haproxy_spoe_name)

        return haproxy_spoe_name

    yield deployer


def deploy_spoe_auth(pytestconfig: pytest.Config, juju: jubilant, app_name, host_name):
    charm_name = "haproxy-spoe-auth"
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        return app_name

    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"{charm_name}_" in f), None
    )
    assert charm_file, f"--charm-file with  {charm_name} charm should be set"

    juju.deploy(
        charm=charm_file,
        app=app_name,
        config={
            "hostname": host_name
        },
    )
    return app_name

def inject_ca_certificate(juju, unit_name, ca_cert: str):
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
