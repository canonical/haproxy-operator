# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy spoe auth."""

import json
import logging
import re
import secrets
import string
import subprocess
import tempfile
import typing
from contextlib import contextmanager

from playwright._impl._driver import compute_driver_executable, get_driver_env
from playwright.sync_api import expect, sync_playwright
import jubilant
import pytest

from .helper import get_unit_ip_address
from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes

@pytest.fixture(scope="session", name="juju")
def lxd_juju_fixture(request: pytest.FixtureRequest) -> str:
    """TODO BOOTSTRAP A CONTROLLER IN LXD, AND ADDS A CLOUD FROM K8S!"""
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

    # we need to swith or commands like add-cloud do not work.
    juju.cli("switch", f"{lxd_controller_name}:", include_model=False)

    def show_debug_log(juju: jubilant.Juju):
        """Show the debug log if tests failed.c

        Args:
            juju: Jubilant juju instance.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    model = request.config.getoption("--model")
    if model:
        try:
            juju.add_model(model=model, cloud=lxd_cloud_name, controller=lxd_controller_name)
        except jubilant.CLIError as err:
            if not "already exists":
                logger.exception(err)
                raise
            juju.model = f"{lxd_controller_name}:{model}"
        juju = jubilant.Juju(model=f"{lxd_controller_name}:{model}")
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(
        keep=keep_models, cloud=lxd_cloud_name, controller=lxd_controller_name
    ) as juju:
        juju.wait_timeout = JUJU_WAIT_TIMEOUT
        yield juju


@pytest.fixture(scope="session", name="k8s_juju")
def k8s_juju_fixture(juju: jubilant.Juju, request: pytest.FixtureRequest) -> str:
    # get clouds. there should be one k8s.
    clouds_json = juju.cli("clouds", "--format=json", include_model=False) # , lxd_cloud_name, lxd_controller_name, include_model=False)
    clouds = json.loads(clouds_json)
    k8s_clouds = [k for k,v in clouds.items() if v['type'] == 'k8s']
    assert len(k8s_clouds) == 1, f"Only one cloud of type k8s supported for the test. {k8s_clouds}"
    k8s_cloud = k8s_clouds[0]

    # Add the k8s cloud to our new controller.
    juju.cli("add-cloud", "--controller", juju.status().model.controller, k8s_cloud, include_model=False)

    new_juju = jubilant.Juju(model=juju.model)
    new_juju.wait_timeout = JUJU_WAIT_TIMEOUT
    k8s_model_name = f"k8s-{juju.status().model.name}"
    try:
        new_juju.add_model(k8s_model_name, k8s_cloud)
    except jubilant.CLIError as err:
        if not "already exists":
            logger.exception(err)
            raise
        new_juju.model = k8s_model_name
    yield new_juju


@pytest.fixture(scope="module", name="iam_bundle")
def deploy_iam_bundle_fixture(k8s_juju: jubilant.Juju):
    """Deploy Canonical identity bundle."""
    # https://github.com/canonical/iam-bundle-integration
    juju = k8s_juju
    if juju.status().apps.get("hydra"):
        logger.info("identity-platform is already deployed")
        return
    juju.deploy("hydra", channel="latest/stable", revision=362, trust=True)
    juju.deploy("kratos", channel="latest/stable", revision=527, trust=True)
    juju.deploy(
        "identity-platform-login-ui-operator", channel="latest/stable", revision=166, trust=True
    )
    juju.deploy("self-signed-certificates", channel="latest/stable", revision=155, trust=True)
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


@contextmanager
def patch_etc_hosts(ip, hostname):
    # I could not come with a better idea...
    etc_host_line = f"{ip} {hostname} #test"
    command_add_line = f"/bin/echo '{etc_host_line}' | sudo tee -a /etc/hosts"
    subprocess.run(command_add_line, shell=True)
    try:
        yield
    finally:
        command_remove_line = f"sudo sed -i '/^{etc_host_line}$/d' /etc/hosts"
        subprocess.run(command_remove_line, shell=True)


@pytest.mark.abort_on_fail
def test_oauth_spoe(
        configured_application_with_tls: str,
        juju: jubilant.Juju,
        k8s_juju: jubilant.Juju,
        any_charm_haproxy_route_requirer: str,
        iam_bundle):


    haproxy_spoe_auth_name = "haproxy-spoe-auth"
    juju.deploy(
        charm="../haproxy-spoe-auth-operator/haproxy-spoe-auth_amd64.charm",
        app=haproxy_spoe_auth_name,
        config={
            "hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
        }
    )
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [80],
                        "hostname": TEST_EXTERNAL_HOSTNAME_CONFIG,
                    }
                ]
            ),
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer,
        )
    )
    ca_cert_result = k8s_juju.run("self-signed-certificates/0", "get-ca-certificate")
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(ca_cert_result.results['ca-certificate'].encode("utf-8"))
        tf.flush()
        # the unit could be not the number 0.
        juju.scp(tf.name, f"{haproxy_spoe_auth_name}/0:/home/ubuntu/iam.crt")
        juju.exec(command="sudo mv /home/ubuntu/iam.crt /usr/local/share/ca-certificates", unit=f"{haproxy_spoe_auth_name}/0")
        juju.exec(command="sudo update-ca-certificates", unit=f"{haproxy_spoe_auth_name}/0")

    k8s_juju.offer(f"{k8s_juju.model}.hydra", endpoint="oauth")
    juju.integrate(f"{k8s_juju.model}.hydra", haproxy_spoe_auth_name)
    juju.integrate(
        f"{configured_application_with_tls}:spoe-auth", haproxy_spoe_auth_name
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer,
            haproxy_spoe_auth_name
        )
    )
    logger.info("juju %s", juju)
    logger.info("juju model %s", juju.model)

    driver_executable, driver_cli = compute_driver_executable()
    completed_process = subprocess.run(
        [driver_executable, driver_cli, "install-deps"], env=get_driver_env()
    )
    logger.info("install-deps output %s", completed_process)
    completed_process = subprocess.run(
        [driver_executable, driver_cli, "install", "chromium"], env=get_driver_env()
    )
    logger.info("install chromium %s", completed_process)

    test_username = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
    test_email = f"{test_username}@example.com"
    test_password = "randompasswd"
    test_secret = test_username
    k8s_juju.run(
        "kratos/0",
        "create-admin-account",
        {"email": test_email, "password": test_password, "username": test_username},
    )
    secret_id = k8s_juju.add_secret(test_secret, {"password": test_password})
    k8s_juju.cli("grant-secret", secret_id, "kratos")
    result = k8s_juju.run(
        "kratos/0",
        "reset-password",
        {"email": test_email, "password-secret-id": secret_id.split(":")[-1]},
    )
    logger.info("results reset-password %s", result.results)

    # TODO I could not find a better way :(
    haproxy_unit_ip = get_unit_ip_address(juju, 'haproxy')
    with patch_etc_hosts(haproxy_unit_ip, TEST_EXTERNAL_HOSTNAME_CONFIG):
        _assert_idp_login_success(test_email, test_password)


def _assert_idp_login_success(test_email, test_password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}")
        logger.info("Page content: %s", page.content())
        expect(page).not_to_have_title(re.compile("Sign in failed"))
        page.get_by_label("Email").fill(test_email)
        page.get_by_label("Password").fill(test_password)
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/")
        logger.info("Content %s", page.content())
        logger.info("url %s", page.url)
        expect(page).to_have_url(f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/")
        assert "ok!" in page.content()
