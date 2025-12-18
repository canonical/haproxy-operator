# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the states of different modes."""

import typing
from unittest.mock import MagicMock, Mock

import ops
import pytest
from charms.haproxy.v0.haproxy_route_tcp import (
    HaproxyRouteTcpRequirerData,
    HaproxyRouteTcpRequirersData,
)
from charms.haproxy.v1.haproxy_route import (
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
)
from charms.tls_certificates_interface.v4.tls_certificates import TLSCertificatesRequiresV4
from charms.traefik_k8s.v1.ingress_per_unit import DataValidationError as V1DataValidationError
from charms.traefik_k8s.v2.ingress import DataValidationError as V2DataValidationError

from state.charm_state import CharmState, ProxyMode
from state.haproxy_route import HaproxyRouteRequirersInformation
from state.haproxy_route_tcp import HAProxyRouteTcpEndpoint
from state.ingress import IngressIntegrationDataValidationError, IngressRequirersInformation
from state.ingress_per_unit import (
    HAProxyBackend,
    IngressPerUnitIntegrationDataValidationError,
    IngressPerUnitRequirersInformation,
)
from state.tls import TLSInformation


def test_ingress_per_unit_from_provider():
    """
    arrange: Setup a mock provider with the required unit data.
    act: Initialize the IngressPerUnitRequirersInformation.
    assert: The state component is initialized correctly with expected data.
    """
    unit_data = {
        "requirer/0": ("juju-unit1.lxd", 8080, True),
        "requirer/1": ("juju-unit2.lxd", 8081, False),
    }

    units = []
    for unit_name in unit_data:
        unit = Mock()
        unit.name = unit_name
        units.append(unit)

    provider = Mock()
    provider.relations = [Mock(units=units)]
    provider.get_data.side_effect = lambda rel, unit: {
        "name": unit.name,
        "model": "test-model",
        "host": unit_data[unit.name][0],
        "port": unit_data[unit.name][1],
        "strip-prefix": unit_data[unit.name][2],
    }

    result = IngressPerUnitRequirersInformation.from_provider(provider)

    expected = [
        HAProxyBackend(
            backend_name="test-model_requirer_0",
            backend_path="test-model-requirer/0",
            hostname_or_ip="juju-unit1.lxd",
            port=8080,
            strip_prefix=True,
        ),
        HAProxyBackend(
            backend_name="test-model_requirer_1",
            backend_path="test-model-requirer/1",
            hostname_or_ip="juju-unit2.lxd",
            port=8081,
            strip_prefix=False,
        ),
    ]
    assert result.backends == expected


def test_ingress_per_unit_from_provider_validation_error():
    """
    arrange: Setup ingress-per-unit provider mock with invalid data.
    act: Initialize the IngressPerUnitRequirersInformation.
    assert: IngressPerUnitIntegrationDataValidationError is raised.
    """
    provider = Mock(relations=[Mock(units=[Mock(name="requirer-charm/0")])])

    provider.get_data.side_effect = V1DataValidationError()

    with pytest.raises(IngressPerUnitIntegrationDataValidationError):
        IngressPerUnitRequirersInformation.from_provider(provider)


def test_ingress_from_provider_validation_error():
    """
    arrange: Setup ingress provider mock with invalid data.
    act: Initialize the IngressRequirersInformation.
    assert: IngressIntegrationDataValidationError is raised.
    """
    provider = Mock(relations=[Mock(units=[Mock(name="requirer-charm/0")])])

    provider.get_data.side_effect = V2DataValidationError()

    with pytest.raises(IngressIntegrationDataValidationError):
        IngressRequirersInformation.from_provider(provider)


def test_proxy_mode_tcp():
    """
    arrange: Setup all relation providers mock.
    act: Initialize the charm state.
    assert: The proxy mode is correctly set to HAPROXY_ROUTE.
    """
    ingress_provider_mock = MagicMock()
    ingress_provider_mock.relations = []
    ingress_per_unit_provider_mock = MagicMock()
    ingress_per_unit_provider_mock.relations = []
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.relations = []
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.relations = [MagicMock(spec=ops.Relation)]
    reverseproxy_requirer_mock = MagicMock()
    reverseproxy_requirer_mock.relations = []
    charm_state = CharmState.from_charm(
        charm=MagicMock(spec=ops.CharmBase),
        ingress_provider=ingress_provider_mock,
        ingress_per_unit_provider=ingress_per_unit_provider_mock,
        haproxy_route_provider=haproxy_route_provider_mock,
        haproxy_route_tcp_provider=haproxy_route_tcp_provider_mock,
        reverseproxy_requirer=reverseproxy_requirer_mock,
    )
    assert charm_state.mode == ProxyMode.HAPROXY_ROUTE


def test_haproxy_route_requirer_information_reserved_ports(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
):
    """
    arrange: Setup mock haproxy-route and haproxy-route-tcp relation providers.
    act: Initialize the HaproxyRouteRequirersInformation state.
    assert: TCP endpoints are not parsed because port 80 is not allowed.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[haproxy_route_tcp_relation_data(port=80)],
            relation_ids_with_invalid_data=[],
        )
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("test"),
            ],
            relation_ids_with_invalid_data=[],
        )
    )
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="test.domain",
        peers=[],
        ca_certs_configured=False,
    )
    assert not haproxy_route_information.valid_tcp_endpoints()
    assert len(haproxy_route_information.relation_ids_with_invalid_data_tcp) == 1


def test_haproxy_route_requirer_information(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
):
    """
    arrange: Setup all relation providers mock.
    act: Initialize the charm state.
    assert: The proxy mode is correctly set to HAPROXY_ROUTE.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[haproxy_route_tcp_relation_data(port=4000)],
            relation_ids_with_invalid_data=[],
        )
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("test"),
            ],
            relation_ids_with_invalid_data=[],
        )
    )
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname=None,
        peers=[],
        ca_certs_configured=False,
    )
    assert len(haproxy_route_information.valid_tcp_endpoints()) == 1


def test_tls_allow_no_certificate():
    """
    arrange: Setup tls-related mocks.
    act: Initialize the TLS state with allow_no_certificates=True.
    assert: The state passes validation even though no certificate is found.
    """
    charm_mock = MagicMock(spec=ops.CharmBase)
    relation_mock = MagicMock(autospec=True)
    relation_mock.data.get = MagicMock(return_value={})
    charm_mock.model.get_relation = MagicMock(return_value=relation_mock)
    certificate_requirer_mock = MagicMock(spec=TLSCertificatesRequiresV4)
    certificate_requirer_mock.get_assigned_certificates = MagicMock(
        return_value=([], "mock private key")
    )
    certificate_requirer_mock.relationship_name = "certificates"
    certificate_requirer_mock.certificate_requests = []
    tls_information = TLSInformation.from_charm(
        charm_mock, certificate_requirer_mock, allow_no_certificates=True
    )
    assert not tls_information.hostnames
    assert tls_information.private_key == "mock private key"


def test_haproxy_route_tcp_endpoint(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Generate TCP relation data.
    act: Initialize the HAProxyRouteTcpEndpoint class with the generated relation data.
    assert: The class correctly parses the information.
    """
    haproxy_route_tcp: HaproxyRouteTcpRequirerData = haproxy_route_tcp_relation_data(port=4000)
    tcp_endpoint = HAProxyRouteTcpEndpoint.from_haproxy_route_tcp_requirer_data(haproxy_route_tcp)
    assert tcp_endpoint.relation_id == haproxy_route_tcp.relation_id
    assert tcp_endpoint.application == haproxy_route_tcp.application
    assert tcp_endpoint.servers[0].address == haproxy_route_tcp.units_data[0].address
    assert tcp_endpoint.servers[0].server_name == f"{haproxy_route_tcp.application}-0"
    assert tcp_endpoint.servers[0].port == haproxy_route_tcp.application_data.backend_port


def test_tcp_http_port_conflict_custom_grpc_port(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Setup TCP endpoint on custom port and HTTP backend with same custom port.
    act: Initialize HaproxyRouteRequirersInformation with both.
    assert: Both TCP endpoint and backend are marked as invalid.
    """
    tcp_relation_id = 0
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[
                haproxy_route_tcp_relation_data(
                    port=5000,
                    relation_id=tcp_relation_id,
                )
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    http_relation_id = 1
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data(
                    "grpc_service",
                    relation_id=http_relation_id,
                    ports=[80],
                    protocol="https",
                    external_grpc_port=5000,
                )
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="haproxy.internal",
        peers=[],
        ca_certs_configured=True,
    )

    assert tcp_relation_id in haproxy_route_information.relation_ids_with_invalid_data_tcp
    assert http_relation_id in haproxy_route_information.relation_ids_with_invalid_data
    assert len(haproxy_route_information.valid_backends()) == 0
    assert len(haproxy_route_information.valid_tcp_endpoints()) == 0


@pytest.mark.parametrize("tcp_port", [80, 443])
def test_tcp_port_conflict_standard_ports(
    tcp_port: int,
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Setup TCP endpoint on standard port (80 or 443) and HTTP backend without external_grpc_port.
    act: Initialize HaproxyRouteRequirersInformation with both.
    assert: Only TCP endpoint is marked as invalid, backend remains valid.
    """
    tcp_relation_id = 0
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[
                haproxy_route_tcp_relation_data(
                    port=tcp_port,
                    relation_id=tcp_relation_id,
                )
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    http_relation_id = 1
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("http_service", relation_id=http_relation_id),
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="haproxy.internal",
        peers=[],
        ca_certs_configured=False,
    )

    assert tcp_relation_id in haproxy_route_information.relation_ids_with_invalid_data_tcp
    assert http_relation_id not in haproxy_route_information.relation_ids_with_invalid_data
    assert len(haproxy_route_information.valid_backends()) == 1
    assert len(haproxy_route_information.valid_tcp_endpoints()) == 0


@pytest.mark.parametrize("grpc_port", [80, 443])
def test_grpc_port_conflict_standard_ports(
    grpc_port: int,
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Setup gRPC backend on standard port (80 or 443) and HTTP backend without external_grpc_port.
    act: Initialize HaproxyRouteRequirersInformation with both.
    assert: Only gRPC backend is marked as invalid, HTTP backend remains valid.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[],
            relation_ids_with_invalid_data=[],
        )
    )

    grpc_relation_id = 1
    http_relation_id = 2
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data(
                    "grpc_service",
                    relation_id=grpc_relation_id,
                    ports=[80],
                    protocol="https",
                    external_grpc_port=grpc_port,
                ),
                haproxy_route_relation_data("http_service", relation_id=http_relation_id),
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="haproxy.internal",
        peers=[],
        ca_certs_configured=True,
    )

    assert grpc_relation_id in haproxy_route_information.relation_ids_with_invalid_data
    assert http_relation_id not in haproxy_route_information.relation_ids_with_invalid_data
    assert len(haproxy_route_information.valid_backends()) == 1


def test_tcp_http_no_conflict_different_ports(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Setup TCP endpoint on port 5000 and HTTP backend with external gRPC port 6000.
    act: Initialize HaproxyRouteRequirersInformation with both.
    assert: Both remain valid as they use different ports.
    """
    tcp_relation_id = 0
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[
                haproxy_route_tcp_relation_data(
                    port=5000,
                    relation_id=tcp_relation_id,
                )
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    http_relation_id = 1
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data(
                    "grpc_service",
                    relation_id=http_relation_id,
                    ports=[80],
                    protocol="https",
                    external_grpc_port=6000,
                )
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="haproxy.internal",
        peers=[],
        ca_certs_configured=True,
    )

    assert tcp_relation_id not in haproxy_route_information.relation_ids_with_invalid_data_tcp
    assert http_relation_id not in haproxy_route_information.relation_ids_with_invalid_data
    assert len(haproxy_route_information.valid_backends()) == 1
    assert len(haproxy_route_information.valid_tcp_endpoints()) == 1


def test_tcp_only_happy_path(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
) -> None:
    """
    arrange: Setup only TCP endpoint without any HTTP backends.
    act: Initialize HaproxyRouteRequirersInformation.
    assert: TCP endpoint remains valid as there are no backends to conflict with.
    """
    tcp_relation_id = 0
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[
                haproxy_route_tcp_relation_data(
                    port=4000,
                    relation_id=tcp_relation_id,
                )
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="test.example.com",
        peers=[],
        ca_certs_configured=False,
    )

    assert len(haproxy_route_information.relation_ids_with_invalid_data_tcp) == 0
    assert len(haproxy_route_information.relation_ids_with_invalid_data) == 0
    assert len(haproxy_route_information.valid_tcp_endpoints()) == 1


def test_tcp_http_no_conflict_no_tcp_endpoints(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Setup only HTTP backend without any TCP endpoints.
    act: Initialize HaproxyRouteRequirersInformation.
    assert: Backend remains valid as there are no TCP endpoints to conflict with.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[],
            relation_ids_with_invalid_data=[],
        )
    )

    http_relation_id = 1
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("http_service", relation_id=http_relation_id),
            ],
            relation_ids_with_invalid_data=[],
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="haproxy.internal",
        peers=[],
        ca_certs_configured=False,
    )

    assert len(haproxy_route_information.relation_ids_with_invalid_data_tcp) == 0
    assert len(haproxy_route_information.relation_ids_with_invalid_data) == 0
    assert len(haproxy_route_information.valid_backends()) == 1
