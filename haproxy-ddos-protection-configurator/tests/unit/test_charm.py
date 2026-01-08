# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

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
            "limit-policy": "reject",
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
