# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for grpc support for the haproxy-route relation."""

import json

import grpc
import jubilant
import pytest
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .grpc_server import echo_pb2, echo_pb2_grpc
from .helper import get_unit_ip_address


@pytest.mark.abort_on_fail
def test_haproxy_route_grpcs_support(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm haproxy route requirer that runs a gRPC server with TLS.

    Assert that:
    - gRPCs requests can be proxied through HAProxy on default and custom ports
    - Header rewrites work correctly for gRPC backends
    - Path rewrites work correctly for gRPC backends
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

    # Configure haproxy-route for gRPC-over-https
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

    # Test gRPC on default port (443)
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

    # Configure gRPC server on custom port with header rewrites
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
                        "load_balancing_algorithm": "source",
                        "protocol": "https",
                        "external_grpc_port": 8443,
                        "header_rewrite_expressions": [
                            ["X-Custom-Header", "RewrittenByHAProxy"],
                        ],
                        "path_rewrite_expressions": [
                            "%[path,regsub(^/v1,)]"
                        ],  # remove /v1 prefix from the path
                        "query_rewrite_expressions": ["should-not-apply=true"],
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

    # Test gRPC on custom port with header rewrite
    with grpc.secure_channel(
        f"{haproxy_ip_address}:8443",
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

        # Test header rewrite functionality
        echo_request = echo_pb2.EchoRequest(message="Header rewrite test")  # type: ignore[attr-defined]
        call_future = echo_stub.Echo.future(echo_request)
        echo_response = call_future.result()
        trailing_metadata = dict(call_future.trailing_metadata())

        # Verify response and that the rewritten header was received by the backend
        assert echo_response.message == "Header rewrite test"
        assert "x-echoed-header" in trailing_metadata
        assert trailing_metadata["x-echoed-header"] == "RewrittenByHAProxy"

    # Test path rewrite functionality by making a request to /v1/echo.EchoService/Echo
    # which should be rewritten to /echo.EchoService/Echo
    with grpc.secure_channel(
        f"{haproxy_ip_address}:8443",
        ssl_credentials,
        options=[
            ("grpc.default_authority", TEST_EXTERNAL_HOSTNAME_CONFIG),
            ("grpc.ssl_target_name_override", TEST_EXTERNAL_HOSTNAME_CONFIG),
        ],
    ) as channel:
        echo_request = echo_pb2.EchoRequest(message="Path rewrite test")  # type: ignore[attr-defined]

        # Call using the versioned path /v1/echo.EchoService/Echo
        versioned_echo = channel.unary_unary(
            "/v1/echo.EchoService/Echo",
            request_serializer=echo_pb2.EchoRequest.SerializeToString,  # type: ignore[attr-defined]
            response_deserializer=echo_pb2.EchoResponse.FromString,  # type: ignore[attr-defined]
        )
        echo_response = versioned_echo(echo_request)

        # If the path rewrite works, we should get the echoed message back
        assert echo_response.message == "Path rewrite test"
