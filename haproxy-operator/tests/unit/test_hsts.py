# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for HSTS header implementation."""

import pathlib
import re
from unittest.mock import ANY, MagicMock

import ops.testing
import pytest

from charm import HAProxyCharm

from .conftest import build_haproxy_route_relation
from .helper import RegexMatcher


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_hsts_disabled(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route.
    act: trigger relation changed.
    assert: haproxy.conf will not set the strict-transport-security response header.
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
    assert (
        "http-response set-header Strict-Transport-Security"
        not in render_file_mock.call_args.args[1]
    )
    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_hsts_enabled(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route and hsts enabled in the config option.
    act: trigger relation changed.
    assert: haproxy.conf will set the strict-transport-security response header.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation],
        config={"enable-hsts": True},
    )
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )
    assert render_file_mock.call_count == 1
    render_file_mock.assert_any_call(
        pathlib.Path("/etc/haproxy/haproxy.cfg"),
        RegexMatcher(
            'http-response set-header Strict-Transport-Security "max-age=2592000" if { ssl_fc } \n'
        ),
        ANY,
    )
    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_hsts_disabled_allow_http(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route with one allow_http domain and hsts enabled.
    act: trigger relation changed.
    assert: haproxy.conf will set the strict-transport-security response header but not for the allow_http domain.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()
    haproxy_route_relation.remote_app_data["allow_http"] = "true"

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation],
        config={"enable-hsts": True},
    )
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )
    assert render_file_mock.call_count == 1
    haproxy_conf_contents = render_file_mock.call_args.args[1]
    assert (
        "acl is_allow_http { req.hdr(host),field(1,:) -i haproxy.internal }"
        in haproxy_conf_contents
    )
    render_file_mock.assert_any_call(
        pathlib.Path("/etc/haproxy/haproxy.cfg"),
        RegexMatcher(
            re.escape(
                'http-response set-header Strict-Transport-Security "max-age=2592000" if { ssl_fc } !is_allow_http\n'
            )
        ),
        ANY,
    )
    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_redirect_uses_named_acl(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route without allow_http.
    act: trigger relation changed.
    assert: haproxy.conf uses the do_not_redirect named ACL for the redirect rule.
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
    haproxy_conf_contents = render_file_mock.call_args.args[1]
    assert "acl do_not_redirect ssl_fc" in haproxy_conf_contents
    assert "http-request redirect scheme https unless do_not_redirect" in haproxy_conf_contents
    assert out.unit_status.name == ops.testing.ActiveStatus.name


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_redirect_allow_http_uses_named_acl(
    monkeypatch: pytest.MonkeyPatch, certificates_integration
):
    """
    arrange: Prepare a haproxy with haproxy_route with allow_http enabled.
    act: trigger relation changed.
    assert: haproxy.conf uses do_not_redirect named ACL with the allow_http condition.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = build_haproxy_route_relation()
    haproxy_route_relation.remote_app_data["allow_http"] = "true"

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, haproxy_route_relation],
    )
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )
    assert render_file_mock.call_count == 1
    haproxy_conf_contents = render_file_mock.call_args.args[1]
    assert "acl do_not_redirect ssl_fc" in haproxy_conf_contents
    assert (
        "acl do_not_redirect { req.hdr(host),field(1,:) -i haproxy.internal }"
        in haproxy_conf_contents
    )
    assert "http-request redirect scheme https unless do_not_redirect" in haproxy_conf_contents
    assert out.unit_status.name == ops.testing.ActiveStatus.name
