# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for https support for the haproxy-route relation."""

import json
import uuid

import httpx
import jubilant
import pytest

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .helper import get_http_version_from_apache2_logs, get_unit_ip_address


@pytest.mark.abort_on_fail
def test_haproxy_route_https_with_different_transport_protocols(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm haproxy route requirer that installs apache2 with ssl.
    Integrate haproxy with certificates and ca transfer.

    Assert that the communication between frontend<->haproxy and haproxy<->backend
        supports both http/2 and http/1.1 transport protocols.
    """
    juju.integrate(
        f"{any_charm_haproxy_route_requirer}:require-tls-certificates",
        f"{certificate_provider_application}:certificates",
    )
    juju.integrate(
        f"{configured_application_with_tls}:receive-ca-certs",
        f"{certificate_provider_application}:send-ca-cert",
    )
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )

    juju.wait(
        lambda status: jubilant.all_active(
            status, any_charm_haproxy_route_requirer, certificate_provider_application
        )
    )

    juju.run(f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "start_ssl_server"})

    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [443],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": True,
                        "protocol": "https",
                    }
                ]
            ),
        },
    )

    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        ),
        delay=5,
    )

    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)

    # Test HTTP/1.1
    request_id = str(uuid.uuid4())
    with httpx.Client(http2=False, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "X-Request-ID": request_id,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert response.http_version == "HTTP/1.1", (
            f"[frontend <-> haproxy] Expected HTTP/1.1, got {response.http_version} "
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer, request_id
    )
    assert http_transport_version == "HTTP/1.1", (
        f"[haproxy <-> backend] Expected HTTP/1.1, got {http_transport_version}"
    )

    # Test HTTP/2 without http/2 support on backend
    request_id = str(uuid.uuid4())
    with httpx.Client(http2=True, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "X-Request-ID": request_id,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert response.http_version == "HTTP/2", (
            f"[frontend <-> haproxy] Expected HTTP/2, got {response.http_version}"
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer, request_id
    )
    assert http_transport_version == "HTTP/1.1", (
        f"[haproxy <-> backend] Expected HTTP/1.1, got {http_transport_version}"
    )

    # Test HTTP/2 with http/2 support on backend
    juju.run(f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "enable_http2"})

    request_id = str(uuid.uuid4())
    with httpx.Client(http2=True, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "X-Request-ID": request_id,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert response.http_version == "HTTP/2", (
            f"[frontend <-> haproxy] Expected HTTP/2, got {response.http_version}"
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju,
        any_charm_haproxy_route_requirer,
        request_id,
    )
    assert http_transport_version == "HTTP/2.0", (
        f"[haproxy <-> backend] Expected HTTP/2, got {http_transport_version}"
    )

    # Test HTTP/1.1 without http/1.1 support on backend
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {"method": "start_ssl_server", "protocols": "h2"},
    )

    request_id = str(uuid.uuid4())
    with httpx.Client(http2=False, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
                "X-Request-ID": request_id,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK, "HTTP/1.1 request failed"
        assert response.http_version == "HTTP/1.1", (
            f"[frontend <-> haproxy] Expected HTTP/1.1, got {response.http_version}"
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer, request_id
    )
    assert http_transport_version == "HTTP/2.0", (
        f"[haproxy <-> backend] Expected HTTP/2, got {http_transport_version}"
    )
