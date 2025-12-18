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
            'acl empty_method   method -i ""',
            "acl has_host hdr(Host) -m found",
            "http-request silent-drop if invalid_method empty_method !has_host",
        ]
    )

    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ddos_protection_disabled(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route and disable-ddos-protection enabled.
    act: trigger relation changed.
    assert: haproxy.cfg will not include DDoS protection ACLs and http-request rules.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation],
        config={"disable-ddos-protection": True},
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
            'acl empty_method   method -i ""',
            "acl has_host hdr(Host) -m found",
            "http-request silent-drop if invalid_method empty_method !has_host",
        ]
    )

    assert out.unit_status.name == ops.testing.ActiveStatus.name
