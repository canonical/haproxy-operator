# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario tests for the rendered haproxy-route-tcp configuration."""

from unittest.mock import MagicMock

import pytest
from ops.testing import Context, State

from charm import HAProxyCharm

from .conftest import build_haproxy_route_tcp_relation


def _render_haproxy_config(
    monkeypatch: pytest.MonkeyPatch,
    tcp_relation,
    certificates_integration,
    peer_relation,
) -> str:
    """Run the charm for a haproxy-route-tcp relation and return the rendered config."""
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    state = State(
        relations=frozenset({peer_relation, certificates_integration, tcp_relation}),
        leader=True,
    )
    context = Context(HAProxyCharm, juju_version="3.6.8")
    context.run(context.on.relation_changed(tcp_relation), state)

    render_file_mock.assert_called_once()
    return render_file_mock.call_args_list[0].args[1]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_haproxy_route_tcp_sticky_sessions_config(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, peer_relation
):
    """
    arrange: Create a haproxy-route-tcp relation with sticky sessions enabled.
    act: Trigger the relation changed event.
    assert: The rendered config contains retries, redispatch, balance source,
        and consistent hashing.
    """
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4444,
        backend_port=4000,
        sni="example.com",
        load_balancing={"algorithm": "source", "consistent_hashing": True},
        retry={"count": 3, "redispatch": True},
    )

    haproxy_config = _render_haproxy_config(
        monkeypatch, tcp_relation, certificates_integration, peer_relation
    )

    assert "retries 3\n    option redispatch" in haproxy_config
    assert "balance source" in haproxy_config
    assert "hash-type consistent" in haproxy_config


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_haproxy_route_tcp_timeouts_config(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, peer_relation
):
    """
    arrange: Create a haproxy-route-tcp relation with timeouts configured.
    act: Trigger the relation changed event.
    assert: The rendered config contains the configured server, connect, and queue timeouts.
    """
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4444,
        backend_port=4000,
        sni="example.com",
        timeout={"server": 10, "connect": 5, "queue": 2},
    )

    haproxy_config = _render_haproxy_config(
        monkeypatch, tcp_relation, certificates_integration, peer_relation
    )

    assert "timeout server 10s" in haproxy_config
    assert "timeout connect 5s" in haproxy_config
    assert "timeout queue 2s" in haproxy_config


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_haproxy_route_tcp_proxy_protocol_config(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, peer_relation
):
    """
    arrange: Create a haproxy-route-tcp relation with PROXY protocol enabled.
    act: Trigger the relation changed event.
    assert: The rendered config sends PROXY protocol v2 to the backend.
    """
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4444,
        backend_port=4000,
        sni="example.com",
        proxy_protocol=True,
    )

    haproxy_config = _render_haproxy_config(
        monkeypatch, tcp_relation, certificates_integration, peer_relation
    )

    assert "send-proxy-v2" in haproxy_config


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_haproxy_route_tcp_port_mapping_config(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, peer_relation
):
    """
    arrange: Create a haproxy-route-tcp relation with a port range mapping.
    act: Trigger the relation changed event.
    assert: The rendered config binds the whole frontend port range.
    """
    tcp_relation = build_haproxy_route_tcp_relation(port_mapping="8080-8090:9080-9090")

    haproxy_config = _render_haproxy_config(
        monkeypatch, tcp_relation, certificates_integration, peer_relation
    )

    assert "bind [::]:8080-8090" in haproxy_config
