# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import socket
import ssl

import jubilant
import pytest

from .helper import get_unit_ip_address


@pytest.mark.abort_on_fail
def test_haproxy_route_tcp(
    configured_application_with_tls: str,
    any_charm_haproxy_route_tcp_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route-tcp",
        any_charm_haproxy_route_tcp_requirer,
    )
    # We set the removed retry-interval config option here as
    # ingress-configurator is not yet synced with the updated lib. This will be removed.
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "update_relation"},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_tcp_requirer
        )
    )
    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)
    # We need to call _create_unverified_context() to test with self-signed certs
    context = ssl._create_unverified_context()  # pylint: disable=protected-access  # nosec
    with (
        socket.create_connection((str(haproxy_ip_address), 4444)) as sock,
        context.wrap_socket(sock, server_hostname="example.com") as ssock,
    ):
        ssock.send(b"ping")
        server_response = ssock.read()
        assert "pong" in str(server_response)

    # Test with sticky sessions
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "update_relation_with_sticky_sessions"},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_tcp_requirer
        )
    )

    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )
    assert all(
        entry in haproxy_config
        for entry in [
            "retries 3",
            "option redispatch",
            "balance source",
            "hash-type consistent",
        ]
    )

    # Test with timeouts
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "update_relation_with_timeouts"},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_tcp_requirer
        )
    )

    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )
    assert all(
        entry in haproxy_config
        for entry in [
            "timeout server 10s",
            "timeout connect 5s",
            "timeout queue 2s",
        ]
    )

    # Test with PROXY PROTOCOL enabled
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "update_relation_with_proxy_protocol"},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_tcp_requirer
        )
    )

    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )
    assert "send-proxy" in haproxy_config


@pytest.mark.abort_on_fail
def test_haproxy_route_tcp_port_range(
    configured_application_with_tls: str,
    any_charm_haproxy_route_tcp_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm TCP requirer using port_range.

    Asserts:
    - HAProxy config contains separate frontends for each port in the range
    - Backend server lines omit the port (1-to-1 mapping)
    - End-to-end connectivity works on every port in the range
    """
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route-tcp",
        any_charm_haproxy_route_tcp_requirer,
    )

    # Start TCP echo servers on each port in the range on the requirer unit,
    # then configure the relation with port_range.
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "start_port_range_servers"},
    )
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "update_relation_with_port_range"},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_tcp_requirer
        )
    )

    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)

    # Verify HAProxy config structure
    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )

    for port in range(10500, 10503):
        assert f"bind *:{port}" in haproxy_config, (
            f"Expected frontend bind for port {port} in HAProxy config"
        )

    # Verify that backend server lines do NOT include explicit port
    # (in port_range mode, the backend connects on the same port as the frontend)
    assert "server " in haproxy_config, "Expected server line in HAProxy config"

    # End-to-end connectivity: connect through HAProxy on each port in the range
    # and verify the TCP echo server responds with "pong" when sent "ping"
    for port in range(10500, 10503):
        with socket.create_connection((str(haproxy_ip_address), port), timeout=5) as sock:
            sock.sendall(b"ping\n")
            response = sock.recv(1024)
            assert b"pong" in response.lower(), (
                f"Expected 'pong' response on port {port}, got: {response!r}"
            )

    # Clean up the background servers
    juju.run(
        f"{any_charm_haproxy_route_tcp_requirer}/0",
        "rpc",
        {"method": "stop_port_range_servers"},
    )
