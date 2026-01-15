# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for HAProxy DDoS protection functionality."""

import json
import logging

import jubilant

logger = logging.getLogger(__name__)

HAPROXY_ROUTE_REQUIRER_NAME = "haproxy-route-requirer"


def test_haproxy_ddos_protection_integration(
    lxd_juju,
    configured_application_with_tls,
    ddos_protection_configurator,
    any_charm_haproxy_route_deployer,
):
    """Test that HAProxy integrates correctly with DDoS protection configurator."""

    any_charm_haproxy_route_deployer(HAPROXY_ROUTE_REQUIRER_NAME)
    lxd_juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", HAPROXY_ROUTE_REQUIRER_NAME
    )
    lxd_juju.wait(
        lambda status: not status.apps[HAPROXY_ROUTE_REQUIRER_NAME].is_waiting,
        timeout=5 * 60,
    )
    lxd_juju.run(
        f"{HAPROXY_ROUTE_REQUIRER_NAME}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": HAPROXY_ROUTE_REQUIRER_NAME,
                        "ports": [80],
                        "hostname": "haproxy1.internal",
                    }
                ]
            ),
        },
    )
    lxd_juju.integrate(
        f"{ddos_protection_configurator}:ddos-protection",
        f"{configured_application_with_tls}:ddos-protection",
    )

    lxd_juju.wait(jubilant.all_active)


def test_haproxy_ddos_protection_configuration(
    lxd_juju: jubilant.Juju,
    configured_application_with_tls: str,
    ddos_protection_configurator: str,
):
    """Test that HAProxy receives correct DDoS protection configuration."""
    lxd_juju.config(
        ddos_protection_configurator,
        {
            "rate-limit-connections-per-minute": 500,
            "limit-policy": "reject",
            "ip-allow-list": "192.168.1.1,10.0.0.0/8",
            "http-request-timeout": 30,
            "http-keepalive-timeout": 5,
            "client-timeout": 60,
            "deny-paths": "/admin,/secret",
        },
    )
    lxd_juju.wait(jubilant.all_active)
    haproxy_cfg = lxd_juju.cli(
        "ssh", f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )

    assert "table ddos_protection_ip" in haproxy_cfg
    assert "tcp-request connection reject if { sc_conn_rate(0) gt 500 }" in haproxy_cfg
    assert "http-request allow if allowed_ips" in haproxy_cfg
    assert "timeout http-request 30000" in haproxy_cfg
    assert "timeout http-keep-alive 5000" in haproxy_cfg
    assert "timeout client 60000" in haproxy_cfg
    assert "http-request deny if denied_paths" in haproxy_cfg
