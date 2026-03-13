# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for publishing proxied endpoints to haproxy-route-tcp relation data."""

import json

import ops
import ops.testing
import pytest

from .conftest import build_haproxy_route_tcp_relation


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_sni_routing(tcp_reconcile_context, peer_relation) -> None:
    """
    arrange: Create a haproxy-route-tcp relation with SNI configured.
    act: Trigger config_changed as leader.
    assert: Proxied endpoints are published as "{sni}:{port}" in the relation data.
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4000,
        sni="api.example.com",
        enforce_tls=True,
        tls_terminate=False,
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation],
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    endpoints = json.loads(out_tcp_relation.local_app_data["endpoints"])
    assert endpoints == ["api.example.com:4000"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_sni_routing_multiple_backends(
    tcp_reconcile_context, peer_relation
) -> None:
    """
    arrange: Create two haproxy-route-tcp relations with SNI on the same port.
    act: Trigger config_changed as leader.
    assert: Each relation gets its own SNI-based endpoint published.
    """
    context, _ = tcp_reconcile_context
    tcp_relation_1 = build_haproxy_route_tcp_relation(
        port=4000,
        sni="api1.example.com",
        enforce_tls=True,
        tls_terminate=False,
        remote_app_name="tcp-requirer-1",
    )
    tcp_relation_2 = build_haproxy_route_tcp_relation(
        port=4000,
        sni="api2.example.com",
        enforce_tls=True,
        tls_terminate=False,
        remote_app_name="tcp-requirer-2",
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation_1, tcp_relation_2],
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation_1 = out.get_relation(tcp_relation_1.id)
    endpoints_1 = json.loads(out_tcp_relation_1.local_app_data["endpoints"])
    assert endpoints_1 == ["api1.example.com:4000"]

    out_tcp_relation_2 = out.get_relation(tcp_relation_2.id)
    endpoints_2 = json.loads(out_tcp_relation_2.local_app_data["endpoints"])
    assert endpoints_2 == ["api2.example.com:4000"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_ha_vip(tcp_reconcile_context, peer_relation) -> None:
    """
    arrange: Create a haproxy-route-tcp relation without SNI and an HA relation with VIP.
    act: Trigger config_changed as leader.
    assert: Proxied endpoints are published as "{vip}:{port}".
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=5000,
        enforce_tls=True,
        tls_terminate=False,
    )
    ha_relation = ops.testing.Relation(
        endpoint="ha",
        interface="hacluster",
        remote_app_name="hacluster",
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation, ha_relation],
        config={"vip": "192.168.1.100"},
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    endpoints = json.loads(out_tcp_relation.local_app_data["endpoints"])
    assert endpoints == ["192.168.1.100:5000"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_peer_unit_addresses(tcp_reconcile_context, peer_relation) -> None:
    """
    arrange: Create a haproxy-route-tcp relation without SNI and without HA.
    act: Trigger config_changed as leader.
    assert: Proxied endpoints are published as "{unit_address}:{port}" for each peer.
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=6000,
        enforce_tls=True,
        tls_terminate=False,
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation],
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    endpoints = json.loads(out_tcp_relation.local_app_data["endpoints"])
    assert endpoints == ["10.0.0.1:6000"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_not_leader(tcp_reconcile_context, peer_relation) -> None:
    """
    arrange: Create a haproxy-route-tcp relation with valid data.
    act: Trigger config_changed as a non-leader unit.
    assert: No proxied endpoints are written to the relation data.
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4000,
        sni="api.example.com",
        enforce_tls=True,
        tls_terminate=False,
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation],
        leader=False,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    assert "endpoints" not in out_tcp_relation.local_app_data


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_sni_with_different_ports(
    tcp_reconcile_context, peer_relation
) -> None:
    """
    arrange: Create two TCP relations with SNI on different ports.
    act: Trigger config_changed as leader.
    assert: Each relation gets its own SNI:port endpoint.
    """
    context, _ = tcp_reconcile_context
    tcp_relation_1 = build_haproxy_route_tcp_relation(
        port=4000,
        sni="api.example.com",
        enforce_tls=True,
        tls_terminate=False,
        remote_app_name="tcp-requirer-1",
    )
    tcp_relation_2 = build_haproxy_route_tcp_relation(
        port=5000,
        sni="web.example.com",
        enforce_tls=True,
        tls_terminate=False,
        remote_app_name="tcp-requirer-2",
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation_1, tcp_relation_2],
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation_1 = out.get_relation(tcp_relation_1.id)
    endpoints_1 = json.loads(out_tcp_relation_1.local_app_data["endpoints"])
    assert endpoints_1 == ["api.example.com:4000"]

    out_tcp_relation_2 = out.get_relation(tcp_relation_2.id)
    endpoints_2 = json.loads(out_tcp_relation_2.local_app_data["endpoints"])
    assert endpoints_2 == ["web.example.com:5000"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_single_backend_no_sni_no_ha(
    tcp_reconcile_context, peer_relation
) -> None:
    """
    arrange: Create a single TCP relation without SNI routing and without HA.
    act: Trigger config_changed as leader.
    assert: Proxied endpoints fall back to peer unit addresses.
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=8080,
        enforce_tls=True,
        tls_terminate=False,
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation],
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    endpoints = json.loads(out_tcp_relation.local_app_data["endpoints"])
    assert endpoints == ["10.0.0.1:8080"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_ha_vip_takes_priority_over_peers(
    tcp_reconcile_context, peer_relation
) -> None:
    """
    arrange: Create a TCP relation without SNI but with HA configured (VIP).
    act: Trigger config_changed as leader.
    assert: VIP is used instead of peer unit addresses.
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4000,
        enforce_tls=True,
        tls_terminate=False,
    )
    ha_relation = ops.testing.Relation(
        endpoint="ha",
        interface="hacluster",
        remote_app_name="hacluster",
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation, ha_relation],
        config={"vip": "10.10.10.10"},
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    endpoints = json.loads(out_tcp_relation.local_app_data["endpoints"])
    assert endpoints == ["10.10.10.10:4000"]


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_tcp_proxied_endpoints_sni_takes_priority_over_ha(
    tcp_reconcile_context, peer_relation
) -> None:
    """
    arrange: Create a TCP relation with both SNI and HA configured.
    act: Trigger config_changed as leader.
    assert: SNI endpoint is published, not the VIP.
    """
    context, _ = tcp_reconcile_context
    tcp_relation = build_haproxy_route_tcp_relation(
        port=4000,
        sni="api.example.com",
        enforce_tls=True,
        tls_terminate=False,
    )
    ha_relation = ops.testing.Relation(
        endpoint="ha",
        interface="hacluster",
        remote_app_name="hacluster",
    )

    state = ops.testing.State(
        relations=[peer_relation, tcp_relation, ha_relation],
        config={"vip": "10.10.10.10"},
        leader=True,
    )
    out = context.run(context.on.config_changed(), state)

    out_tcp_relation = out.get_relation(tcp_relation.id)
    endpoints = json.loads(out_tcp_relation.local_app_data["endpoints"])
    assert endpoints == ["api.example.com:4000"]
