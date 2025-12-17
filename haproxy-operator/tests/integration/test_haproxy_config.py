# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy configurations."""

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_ddos_protection_enabled(
    application: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm.
    act: Retrieve the haproxy config file.
    assert: The DDoS protection rules are present in the config.
    """
    juju.wait(
        lambda status: jubilant.all_active(status, application),
        timeout=300,
    )

    haproxy_config = juju.ssh(f"{application}/0", "cat /etc/haproxy/haproxy.cfg")

    assert "acl invalid_method" in haproxy_config
    assert "acl empty_method" in haproxy_config
    assert "acl missing_host" in haproxy_config
    assert "http-request silent-drop" in haproxy_config


@pytest.mark.abort_on_fail
def test_ddos_protection_disabled(
    configured_application_with_tls: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm.
    act: Update the disable-ddos-protection config and retrieve the haproxy config.
    assert: The DDoS protection rules are not present in the config.
    """
    juju.config(configured_application_with_tls, {"disable-ddos-protection": True})
    juju.wait(
        lambda status: jubilant.all_active(status, configured_application_with_tls),
        timeout=300,
    )

    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )

    assert "acl invalid_method" not in haproxy_config
    assert "acl empty_method" not in haproxy_config
    assert "acl missing_host" not in haproxy_config
    assert "http-request silent-drop" not in haproxy_config
