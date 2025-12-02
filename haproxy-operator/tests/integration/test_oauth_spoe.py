# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy spoe auth."""

import json
import logging
import typing

import jubilant
import pytest

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes

@pytest.fixture(scope="session", name="juju")
def lxd_juju_fixture(request: pytest.FixtureRequest) -> str:
    """TODO BOOTSTRAP A CONTROLLER IN LXD, AND ADDS A CLOUD FROM K8S!"""
    juju = jubilant.Juju()

    lxd_controller_name = "localhost"
    lxd_cloud_name = "localhost"
    juju.wait_timeout = JUJU_WAIT_TIMEOUT
    juju.bootstrap(lxd_cloud_name, lxd_controller_name)

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
        juju.add_model(model=model, cloud=lxd_cloud_name, controller=lxd_controller_name)
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
    new_juju.add_model(f"k8s-{juju.status().model.name}", k8s_cloud)
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

@pytest.mark.abort_on_fail
def test_oauth_spoe(
        juju: jubilant.Juju,
        k8s_juju: jubilant.Juju,
        iam_bundle):
    logger.info("juju %s", juju)
    logger.info("juju model %s", juju.model)
    import pdb; pdb.set_trace()
    assert False
