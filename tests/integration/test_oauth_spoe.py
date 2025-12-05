# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy spoe auth."""
import json
import logging
import re
import secrets
import string

import requests
import jubilant
import pytest
from playwright.sync_api import expect, sync_playwright

from .helper import get_unit_ip_address, patch_etc_hosts

logger = logging.getLogger(__name__)

JUJU_WAIT_TIMEOUT = 10 * 60  # 10 minutes


@pytest.mark.abort_on_fail
def test_oauth_spoe(
    configured_application_with_tls: str,
    juju: jubilant.Juju,
    k8s_juju: jubilant.Juju,
    any_charm_haproxy_route_deployer,
    iam_bundle,
    haproxy_spoe_auth_deployer,
    browser_context_manager,
):
    host_protected_1 = "haproxy1.internal"
    host_protected_2 = "haproxy2.internal"
    host_not_protected = "haproxy3.internal"
    haproxy_route_requirer_1 = any_charm_haproxy_route_deployer("haproxy-route-requirer1")
    haproxy_spoe_auth_1 = haproxy_spoe_auth_deployer("haproxy-spoe-auth1", host_protected_1)
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", haproxy_route_requirer_1
    )
    juju.run(
        f"{haproxy_route_requirer_1}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry_1",
                        "ports": [80],
                        "hostname": host_protected_1,
                    }
                ]
            ),
        },
    )

    haproxy_route_requirer_2 = any_charm_haproxy_route_deployer("haproxy-route-requirer2")
    haproxy_spoe_auth_2 = haproxy_spoe_auth_deployer("haproxy-spoe-auth2", host_protected_2)
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", haproxy_route_requirer_2
    )
    juju.wait(lambda status: not status.apps[haproxy_route_requirer_2].is_waiting, timeout=5 * 60)
    juju.run(
        f"{haproxy_route_requirer_2}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry_2",
                        "ports": [80],
                        "hostname": host_protected_2,
                    }
                ]
            ),
        },
    )
    haproxy_route_requirer_3 = any_charm_haproxy_route_deployer("haproxy-route-requirer3")
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", haproxy_route_requirer_3
    )
    juju.wait(lambda status: not status.apps[haproxy_route_requirer_3].is_waiting, timeout=5 * 60)
    juju.run(
        f"{haproxy_route_requirer_3}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry_3",
                        "ports": [80],
                        "hostname": host_not_protected,
                    }
                ]
            ),
        },
    )
    
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            configured_application_with_tls,
            haproxy_route_requirer_1,
            haproxy_spoe_auth_1,
            haproxy_route_requirer_2,
            haproxy_spoe_auth_2,
            haproxy_route_requirer_3,
        )
    )

    test_email, test_password = create_idp_user(k8s_juju)
    logger.info("test_email:%s test_password:%s", test_email, test_password)

    haproxy_unit_ip = get_unit_ip_address(juju, "haproxy")

    with patch_etc_hosts(haproxy_unit_ip, host_not_protected):
        response = requests.get(f"https://{host_not_protected}", timeout=5, verify=False)
        assert "ok!" in response.text
        assert host_not_protected in response.text
    with patch_etc_hosts(haproxy_unit_ip, host_protected_1):
        _assert_idp_login_success(host_protected_1, test_email, test_password)
    # This opens a new browser, so sessions are not reused. We could
    # instead try to reuse.
    with patch_etc_hosts(haproxy_unit_ip, host_protected_2):
        _assert_idp_login_success(host_protected_2, test_email, test_password)



def _assert_idp_login_success(hostname, test_email, test_password):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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
