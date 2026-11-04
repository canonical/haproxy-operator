# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for DDoS protection rules implementation."""

from unittest.mock import MagicMock

import ops.testing
import pytest

from charm import HAProxyCharm

from .conftest import build_haproxy_route_relation


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ddos_protection_enabled(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route.
    act: trigger relation changed.
    assert: haproxy.cfg will include DDoS protection ACLs and http-request rules.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation],
        leader=True,
    )
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )
    assert render_file_mock.call_count == 1
    config_content = render_file_mock.call_args.args[1]

    assert all(
        entry in config_content
        for entry in [
            "acl invalid_method method TRACE TRACK DEBUG",
            'acl empty_method method -i ""',
            "acl has_host hdr(Host) -m found",
            "http-request silent-drop if invalid_method empty_method !has_host",
            "timeout http-request 60000",
            "timeout http-keep-alive 30000",
            "timeout client 50000",
        ]
    )

    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ddos_protection_disabled(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route and ddos-protection disabled.
    act: trigger relation changed.
    assert: haproxy.cfg will not include DDoS protection ACLs, http-request rules, and protective timeouts.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation],
        config={"ddos-protection": False},
        leader=True,
    )
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )
    assert render_file_mock.call_count == 1
    config_content = render_file_mock.call_args.args[1]

    assert not any(
        entry in config_content
        for entry in [
            "acl invalid_method method TRACE TRACK DEBUG",
            'acl empty_method method -i ""',
            "acl has_host hdr(Host) -m found",
            "http-request silent-drop if invalid_method empty_method !has_host",
            "timeout http-request 60000",
            "timeout http-keep-alive 30000",
            "timeout client 50000",
        ]
    )

    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ddos_protection_configuration_from_relation(
    monkeypatch: pytest.MonkeyPatch, certificates_integration
):
    """
    arrange: Prepare a haproxy with a ddos-protection relation carrying configuration.
    act: trigger the ddos-protection relation changed event.
    assert: haproxy.cfg includes the configured limits, policies and timeouts.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()
    ddos_relation = ops.testing.Relation(
        "ddos-protection",
        interface="ddos_protection",
        remote_app_data={
            "rate_limit_connections_per_minute": "500",
            "limit_policy_tcp": '"reject"',
            "ip_allow_list": '["192.168.1.1", "10.0.0.0/8"]',
            "http_request_timeout": "30",
            "http_keepalive_timeout": "5",
            "client_timeout": "60",
            "deny_paths": '["/admin", "/secret"]',
        },
    )

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation, ddos_relation],
        leader=True,
    )
    out = ctx.run(
        ctx.on.relation_changed(ddos_relation),
        state,
    )
    config_content = render_file_mock.call_args.args[1]

    assert all(
        entry in config_content
        for entry in [
            "table ddos_protection_ip",
            "tcp-request connection reject if { sc_conn_rate(0) gt 500 }",
            "http-request allow if allowed_ips",
            "timeout http-request 30s",
            "timeout http-keep-alive 5s",
            "timeout client 60s",
            "http-request deny if denied_paths",
        ]
    )

    assert out.unit_status.name == ops.testing.ActiveStatus.name
