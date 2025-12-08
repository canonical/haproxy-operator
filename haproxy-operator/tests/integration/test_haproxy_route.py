# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import json
import uuid

import grpc
import httpx
import jubilant
import pytest
import requests
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .grpc_server import echo_pb2, echo_pb2_grpc
from .helper import get_http_version_from_apache2_logs, get_unit_ip_address


@pytest.mark.abort_on_fail
def test_haproxy_route_any_charm_requirer(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
    # We set the removed retry-interval config option here as
    # ingress-configurator is not yet synced with the updated lib. This will be removed.
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [80],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": True,
                    }
                ]
            ),
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
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
            "option http-server-close",
            "balance source",
            "hash-type consistent",
        ]
    )


@pytest.mark.abort_on_fail
def test_haproxy_route_protocol_https(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm haproxy route requirer that installs apache2 with ssl.
    Integrate haproxy with certificates and ca transfer.

    Assert that the requirer endpoints can be accessed using https.
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
                        "allow_http": True,
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
    response = requests.get(
        f"https://{haproxy_ip_address}",
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        timeout=5,
        verify=False,  # nosec: B501
    )
    assert response.text == "ok!"

    # Make HTTP request to verify allow_http works
    response = requests.get(
        f"http://{haproxy_ip_address}",
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        timeout=5,
    )
    assert response.text == "ok!"


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


@pytest.mark.abort_on_fail
def test_haproxy_route_grpcs_support(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm haproxy route requirer that runs a gRPC server with TLS.

    Assert that gRPCs requests can be proxied through HAProxy.
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

    # Start gRPC SSL server
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "start_ssl_server",
            "kwargs": json.dumps({"grpc": True}),
        },
    )

    # Configure haproxy-route for gRPC
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [50051],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": False,
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
    )
    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)

    ca_cert_content = juju.run(f"{certificate_provider_application}/0", "get-ca-certificate")

    ssl_credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_cert_content.results["ca-certificate"].encode()
    )

    with grpc.secure_channel(
        f"{haproxy_ip_address}:443",
        ssl_credentials,
        options=[
            ("grpc.default_authority", TEST_EXTERNAL_HOSTNAME_CONFIG),
            ("grpc.ssl_target_name_override", TEST_EXTERNAL_HOSTNAME_CONFIG),
        ],
    ) as channel:
        reflection_stub = reflection_pb2_grpc.ServerReflectionStub(channel)

        request = reflection_pb2.ServerReflectionRequest(list_services="")
        response = reflection_stub.ServerReflectionInfo(iter([request]))
        # make a call to ensure we get a response
        service_names = set()
        for resp in response:
            for service in resp.list_services_response.service:
                service_names.add(service.name)

        assert {"echo.EchoService", "grpc.reflection.v1alpha.ServerReflection"} == service_names

        echo_request = echo_pb2.EchoRequest(message="Test!")  # type: ignore[attr-defined]
        echo_stub = echo_pb2_grpc.EchoServiceStub(channel)
        echo_response = echo_stub.Echo(echo_request)
        assert echo_response.message == "Test!"
