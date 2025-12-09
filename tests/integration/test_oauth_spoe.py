# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy spoe auth."""

import json
import logging
import re
import secrets
import string
from collections import namedtuple

import jubilant
import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from .helper import get_unit_ip_address

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes


@pytest.mark.abort_on_fail
def test_oauth_spoe(
    configured_application_with_tls: str,
    lxd_juju: jubilant.Juju,
    k8s_juju: jubilant.Juju,
    any_charm_haproxy_route_deployer,
    iam_bundle,
    haproxy_spoe_auth_deployer,
    browser_context_manager,
):
    """
    Deploy haproxy.
    Deploy three anycharms that implement haproxy-route using three different hostnames.
    Protect two of them with haproxy-spoe-auth.
    The two protected ones should require OIDC authentication.
    The unprotected one can be accessed directly.
    """
    HostConfig = namedtuple("HostConfig", ["hostname", "requirer", "spoe"])
    host_configs = [
        HostConfig(
            "haproxy1.internal", "haproxy-route-requirer1", "haproxy-spoe-auth1"
        ),
        HostConfig(
            "haproxy2.internal", "haproxy-route-requirer2", "haproxy-spoe-auth2"
        ),
        # Unprotected hostname
        HostConfig("haproxy3.internal", "haproxy-route-requirer3", None),
    ]

    # Deploy the haproxy-requirer integration charms and she haproxy-spoe-auth charms
    for host_config in host_configs:
        any_charm_haproxy_route_deployer(host_config.requirer)
        if host_config.spoe:
            haproxy_spoe_auth_deployer(host_config.spoe, host_config.hostname)

    # Integrate haproxy-requirer integration charms with haproxy and set the relation data.
    for host_config in host_configs:
        lxd_juju.integrate(
            f"{configured_application_with_tls}:haproxy-route", host_config.requirer
        )
        lxd_juju.wait(
            lambda status: not status.apps[host_config.requirer].is_waiting,
            timeout=5 * 60,
        )
        lxd_juju.run(
            f"{host_config.requirer}/0",
            "rpc",
            {
                "method": "update_relation",
                "args": json.dumps(
                    [
                        {
                            "service": host_config.requirer,
                            "ports": [80],
                            "hostname": host_config.hostname,
                        }
                    ]
                ),
            },
        )
    lxd_juju.wait(jubilant.all_active)

    test_email, test_password = create_idp_user(k8s_juju)
    logger.info("test_email:%s test_password:%s", test_email, test_password)

    haproxy_unit_ip = get_unit_ip_address(lxd_juju, "haproxy")

    for host_config in host_configs:
        if host_config.spoe:
            logger.info("Testing protected %s", host_config.hostname)
            _assert_idp_login_success(
                haproxy_unit_ip, host_config.hostname, test_email, test_password
            )
        else:
            logger.info("Testing unprotected %s", host_config.hostname)
            response = requests.get(
                f"https://{haproxy_unit_ip}",
                headers={"Host": host_config.hostname},
                timeout=5,
                verify=False,
            )
            assert "ok!" in response.text
            assert host_config.hostname in response.text


def _assert_idp_login_success(haproxy_unit_ip, hostname, test_email, test_password):
    """Test OIDC authentication. After authenticating, the hostname is in the response."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[f"--host-resolver-rules=MAP {hostname} {haproxy_unit_ip}"],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(f"https://{hostname}")
        logger.info("Page content: %s", page.content())
        expect(page).not_to_have_title(re.compile("Sign in failed"))
        # This will timeout if there is no email field.
        page.get_by_label("Email").fill(test_email)
        page.get_by_label("Password").fill(test_password)
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(f"https://{hostname}/")
        logger.info("Content %s", page.content())
        logger.info("url %s", page.url)
        expect(page).to_have_url(f"https://{hostname}/")
        assert "ok!" in page.content()
        assert hostname in page.content()


def create_idp_user(k8s_juju) -> tuple[str, str]:
    """Create a user (admin account) in Canonical IDP."""
    test_username = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
    test_email = f"{test_username}@example.com"
    test_password = secrets.token_hex(8)
    test_secret = test_username
    logger.info("username: %s, password: %s", test_username, test_password)
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
    return test_email, test_password
