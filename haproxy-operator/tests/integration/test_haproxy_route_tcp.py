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
    haproxy_route_tcp_relation: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
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
