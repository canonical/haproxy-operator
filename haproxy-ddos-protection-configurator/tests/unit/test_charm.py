# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json

from ops import testing

from charm import HAProxyDDoSProtectionConfiguratorCharm


def test_charm_starts_successfully():
    """
    arrange: Create a charm context.
    act: Run the start event.
    assert: Unit status is ActiveStatus.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(leader=True)
    out = ctx.run(ctx.on.start(), state)
    assert out.unit_status == testing.ActiveStatus()


def test_config_changed_with_valid_config():
    """
    arrange: Create a charm context with complete valid DDoS protection configuration.
    act: Run the config-changed event.
    assert: Unit status is ActiveStatus.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(
        leader=True,
        config={
            "rate-limit-requests-per-minute": 100,
            "rate-limit-connections-per-minute": 50,
            "concurrent-connections-limit": 1000,
            "error-rate-per-minute": 10,
            "limit-policy-http": "reject",
            "limit-policy-tcp": "reject",
            "ip-allow-list": "192.168.1.1, 192.168.1.0/24",
            "http-request-timeout": 30,
            "http-keepalive-timeout": 60,
            "client-timeout": 50,
            "deny-paths": "/admin, /internal",
        },
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == testing.ActiveStatus()


def test_config_changed_with_invalid_rate_limit_requests():
    """
    arrange: Create a charm context with negative rate-limit-requests-per-minute.
    act: Run the config-changed event.
    assert: Unit status is BlockedStatus.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(
        leader=True,
        config={
            "rate-limit-requests-per-minute": -100,
        },
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert isinstance(out.unit_status, testing.BlockedStatus)


def test_config_changed_saves_relation_data():
    """
    arrange: Create a charm context with a ddos-protection relation and valid config.
    act: Run the config-changed event.
    assert: The validated configuration is saved to the relation app databag.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    relation = testing.Relation("ddos-protection", interface="ddos_protection")
    state = testing.State(
        leader=True,
        relations=[relation],
        config={
            "rate-limit-requests-per-minute": 100,
            "rate-limit-connections-per-minute": 50,
            "limit-policy-http": "reject",
            "limit-policy-tcp": "reject",
            "ip-allow-list": "192.168.1.1, 192.168.1.0/24",
            "deny-paths": "/admin, /internal",
        },
    )

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    out_relation = next(rel for rel in out.relations if rel.endpoint == "ddos-protection")
    assert out_relation.local_app_data is not None
    local_app_data = out_relation.local_app_data
    assert json.loads(local_app_data["rate_limit_requests_per_minute"]) == 100
    assert json.loads(local_app_data["rate_limit_connections_per_minute"]) == 50
    assert json.loads(local_app_data["limit_policy_http"]) == "reject"
    assert json.loads(local_app_data["limit_policy_tcp"]) == "reject"
    assert json.loads(local_app_data["ip_allow_list"]) == [
        "192.168.1.1",
        "192.168.1.0/24",
    ]
    assert json.loads(local_app_data["deny_paths"]) == ["/admin", "/internal"]
