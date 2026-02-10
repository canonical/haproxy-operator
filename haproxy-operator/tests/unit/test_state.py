# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the states of different modes."""

import typing
from ipaddress import IPv4Address
from unittest.mock import MagicMock, Mock

import ops
import pytest
from charms.haproxy.v0.ddos_protection import (
    DDoSProtectionInvalidRelationDataError,
    DDoSProtectionProviderAppData,
    DDoSProtectionRequirer,
)
from charms.haproxy.v1.haproxy_route_tcp import (
    HaproxyRouteTcpRequirerData,
    HaproxyRouteTcpRequirersData,
)
from charms.haproxy.v2.haproxy_route import (
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
)
from charms.tls_certificates_interface.v4.tls_certificates import (
    TLSCertificatesRequiresV4,
)
from charms.traefik_k8s.v1.ingress_per_unit import (
    DataValidationError as V1DataValidationError,
)
from charms.traefik_k8s.v2.ingress import DataValidationError as V2DataValidationError

from state.charm_state import CharmState, ProxyMode
from state.ddos_protection import DDosProtection, DDosProtectionValidationError
from state.haproxy_route import (
    HAProxyRouteBackend,
    HaproxyRouteRequirersInformation,
    HAProxyRouteServer,
    generate_hostname_acls,
    parse_haproxy_route_tcp_requirers_data,
)
from state.haproxy_route_tcp import (
    HAProxyRouteTcpBackend,
    HAProxyRouteTcpFrontend,
    HAProxyRouteTcpFrontendValidationError,
)
from state.ingress import (
    IngressIntegrationDataValidationError,
    IngressRequirersInformation,
)
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

    result = IngressPerUnitRequirersInformation.from_provider(provider, peers=[])

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
        IngressPerUnitRequirersInformation.from_provider(provider, peers=[])


def test_ingress_from_provider_validation_error():
    """
    arrange: Setup ingress provider mock with invalid data.
    act: Initialize the IngressRequirersInformation.
    assert: IngressIntegrationDataValidationError is raised.
    """
    provider = Mock(relations=[Mock(units=[Mock(name="requirer-charm/0")])])

    provider.get_data.side_effect = V2DataValidationError()

    with pytest.raises(IngressIntegrationDataValidationError):
        IngressRequirersInformation.from_provider(provider, peers=[])


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
            relation_ids_with_invalid_data=set(),
        )
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("test"),
            ],
            relation_ids_with_invalid_data=set(),
        )
    )
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="test.domain",
        peers=[],
        ca_certs_configured=False,
    )
    assert not haproxy_route_information.valid_tcp_frontends()
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
            relation_ids_with_invalid_data=set(),
        )
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("test"),
            ],
            relation_ids_with_invalid_data=set(),
        )
    )
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname=None,
        peers=[],
        ca_certs_configured=False,
    )
    assert len(haproxy_route_information.valid_tcp_frontends()) == 1


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
    act: Initialize the HAProxyRouteTcpBackend class with the generated relation data.
    assert: The class correctly parses the information.
    """
    haproxy_route_tcp: HaproxyRouteTcpRequirerData = haproxy_route_tcp_relation_data(port=4000)
    tcp_endpoint = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(haproxy_route_tcp)
    assert tcp_endpoint.relation_id == haproxy_route_tcp.relation_id
    assert tcp_endpoint.application == haproxy_route_tcp.application
    assert tcp_endpoint.servers[0].address == haproxy_route_tcp.units_data[0].address
    assert tcp_endpoint.servers[0].server_name == f"{haproxy_route_tcp.application}-0"
    assert tcp_endpoint.servers[0].port == haproxy_route_tcp.application_data.backend_port


def test_tcp_grpc_port_conflict(
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
            relation_ids_with_invalid_data=set(),
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
            relation_ids_with_invalid_data=set(),
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
    assert len(haproxy_route_information.valid_tcp_frontends()) == 0


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
            relation_ids_with_invalid_data=set(),
        )
    )

    http_relation_id = 1
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("http_service", relation_id=http_relation_id),
            ],
            relation_ids_with_invalid_data=set(),
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
    assert len(haproxy_route_information.valid_tcp_frontends()) == 0


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
            relation_ids_with_invalid_data=set(),
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
            relation_ids_with_invalid_data=set(),
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


def test_tcp_grpc_different_ports(
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
            relation_ids_with_invalid_data=set(),
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
            relation_ids_with_invalid_data=set(),
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
    assert len(haproxy_route_information.valid_tcp_frontends()) == 1


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
            relation_ids_with_invalid_data=set(),
        )
    )

    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[],
            relation_ids_with_invalid_data=set(),
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
    assert len(haproxy_route_information.valid_tcp_frontends()) == 1


def test_http_only_happy_path(
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
            relation_ids_with_invalid_data=set(),
        )
    )

    http_relation_id = 1
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data("http_service", relation_id=http_relation_id),
            ],
            relation_ids_with_invalid_data=set(),
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


@pytest.mark.parametrize(
    "ddos_protection,expected_value",
    [(False, False), (True, True)],
    ids=["protection_disabled", "protection_enabled"],
)
def test_charm_state_ddos_protection(ddos_protection, expected_value):
    """
    arrange: Setup a mock charm with ddos-protection config.
    act: Initialize the CharmState from the charm.
    assert: The ddos_protection field matches the expected value.
    """
    charm_mock = MagicMock(spec=ops.CharmBase)
    charm_mock.config.get.side_effect = lambda key: {
        "global-maxconn": 4096,
        "enable-hsts": False,
        "ddos-protection": ddos_protection,
    }.get(key)

    ingress_provider_mock = MagicMock()
    ingress_provider_mock.relations = []
    ingress_per_unit_provider_mock = MagicMock()
    ingress_per_unit_provider_mock.relations = []
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.relations = []
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.relations = []
    reverseproxy_requirer_mock = MagicMock()
    reverseproxy_requirer_mock.relations = []

    charm_state = CharmState.from_charm(
        charm=charm_mock,
        ingress_provider=ingress_provider_mock,
        ingress_per_unit_provider=ingress_per_unit_provider_mock,
        haproxy_route_provider=haproxy_route_provider_mock,
        haproxy_route_tcp_provider=haproxy_route_tcp_provider_mock,
        reverseproxy_requirer=reverseproxy_requirer_mock,
    )

    assert charm_state.ddos_protection is expected_value


@pytest.mark.parametrize(
    "ddos_kwargs, expected",
    [
        (
            {
                "limit_policy_http": "reject",
                "rate_limit_requests_per_minute": 100,
                "concurrent_connections_limit": 50,
            },
            True,
        ),
        (
            {
                "limit_policy_tcp": "reject",
                "concurrent_connections_limit": 50,
            },
            True,
        ),
        (
            {
                "limit_policy_http": "reject",
            },
            False,
        ),
        (
            {
                "rate_limit_requests_per_minute": 100,
                "concurrent_connections_limit": 50,
            },
            False,
        ),
    ],
    ids=[
        "http_policy_and_metrics_configured",
        "tcp_policy_and_metrics_configured",
        "policy_without_metrics",
        "metrics_without_policy",
    ],
)
def test_ddos_protection_has_rate_limiting(ddos_kwargs, expected):
    """
    arrange: Call DDosProtection with various rate limit configurations.
    act: Check has_rate_limiting property.
    assert: has_rate_limiting matches expected value.
    """
    ddos_protection = DDosProtection(**ddos_kwargs)

    assert ddos_protection.has_rate_limiting is expected


def test_ddos_protection_from_charm_no_config():
    """
    arrange: Create mock DDoSProtectionRequirer that returns no config.
    act: Call DDosProtection.from_charm.
    assert: Returns empty DDosProtection instance.
    """
    mock_ddos_requirer = MagicMock(spec=DDoSProtectionRequirer)
    mock_ddos_requirer.get_ddos_config.return_value = None

    result = DDosProtection.from_charm(mock_ddos_requirer)

    assert result == DDosProtection()


def test_ddos_protection_from_charm_with_config():
    """
    arrange: Create mock DDoSProtectionRequirer with full configuration.
    act: Call DDosProtection.from_charm.
    assert: Returns DDosProtection with all fields populated correctly.
    """
    config = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=1000,
        rate_limit_connections_per_minute=500,
        concurrent_connections_limit=100,
        error_rate=50,
        limit_policy_http="reject",
        policy_status_code=429,
        http_request_timeout=30,
        http_keepalive_timeout=5,
        client_timeout=60,
        ip_allow_list=["192.168.1.1", "10.0.0.0/8"],
        deny_paths=["/admin", "/secret"],
    )

    ddos_requirer = MagicMock(spec=DDoSProtectionRequirer)
    ddos_requirer.get_ddos_config.return_value = config
    result = DDosProtection.from_charm(ddos_requirer)

    assert result.rate_limit_requests_per_minute == 1000
    assert result.rate_limit_connections_per_minute == 500
    assert result.concurrent_connections_limit == 100
    assert result.error_rate == 50
    assert result.limit_policy_http == "reject"
    assert result.limit_policy_tcp == "silent-drop"
    assert result.policy_status_code == 429

    assert result.http_request_timeout == 30000
    assert result.http_keepalive_timeout == 5000
    assert result.client_timeout == 60000

    assert result.ip_allow_list == ["192.168.1.1", "10.0.0.0/8"]
    assert result.deny_paths == ["/admin", "/secret"]


def test_ddos_protection_from_charm_relation_data_error():
    """
    arrange: Create mock DDoSProtectionRequirer that raises relation data error.
    act: Call DDosProtection.from_charm.
    assert: Raises DDosProtectionValidationError with wrapped error.
    """
    mock_ddos_requirer = MagicMock(spec=DDoSProtectionRequirer)
    mock_ddos_requirer.get_ddos_config.side_effect = DDoSProtectionInvalidRelationDataError(
        "Invalid relation data"
    )

    with pytest.raises(DDosProtectionValidationError) as exc_info:
        DDosProtection.from_charm(mock_ddos_requirer)

    assert "Failed to load DDoS protection configuration" in str(exc_info.value)
    assert "Invalid relation data" in str(exc_info.value)


def test_haproxy_route_backend_wildcard_hostname_acls(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HAProxyRouteBackend with mixed wildcard and standard hostnames.
    act: Get wildcard_hostname_acls property.
    assert: Returns base domains (without *.) for wildcard hostnames.
    """
    requirer_data = haproxy_route_relation_data("test_service", relation_id=1)
    backend = HAProxyRouteBackend(
        relation_id=1,
        application_data=requirer_data.application_data,
        servers=[
            HAProxyRouteServer(
                server_name="test-0",
                address=IPv4Address("10.0.0.1"),
                port=80,
                protocol="http",
                check=None,
                maxconn=None,
            )
        ],
        hostname_acls={"example.com", "*.example.com", "test.example.com", "*.test.com"},
    )

    wildcard_acls = backend.wildcard_hostname_acls

    # wildcard_hostname_acls returns domains with leading dot (stripped of * only) from wildcard hostnames
    assert wildcard_acls == {".example.com", ".test.com"}
    assert "*.example.com" not in wildcard_acls
    assert "*.test.com" not in wildcard_acls


def test_haproxy_route_backend_standard_hostname_acls(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HAProxyRouteBackend with mixed wildcard and standard hostnames.
    act: Get standard_hostname_acls property.
    assert: Returns only hostnames that do NOT start with '*.'.
    """
    requirer_data = haproxy_route_relation_data("test_service", relation_id=1)
    backend = HAProxyRouteBackend(
        relation_id=1,
        application_data=requirer_data.application_data,
        servers=[
            HAProxyRouteServer(
                server_name="test-0",
                address=IPv4Address("10.0.0.1"),
                port=80,
                protocol="http",
                check=None,
                maxconn=None,
            )
        ],
        hostname_acls={"example.com", "*.example.com", "test.example.com", "*.test.com"},
    )

    standard_acls = backend.standard_hostname_acls

    # standard_hostname_acls returns hostnames that do NOT start with *.
    assert standard_acls == {"example.com", "test.example.com"}
    assert "*.example.com" not in standard_acls
    assert "*.test.com" not in standard_acls


def test_haproxy_route_backend_only_wildcard_hostnames(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HAProxyRouteBackend with only wildcard hostnames.
    act: Get wildcard_hostname_acls and standard_hostname_acls properties.
    assert: wildcard_hostname_acls contains base domains, standard_hostname_acls is empty.
    """
    requirer_data = haproxy_route_relation_data("test_service", relation_id=1)
    backend = HAProxyRouteBackend(
        relation_id=1,
        application_data=requirer_data.application_data,
        servers=[
            HAProxyRouteServer(
                server_name="test-0",
                address=IPv4Address("10.0.0.1"),
                port=80,
                protocol="http",
                check=None,
                maxconn=None,
            )
        ],
        hostname_acls={"*.example.com", "*.test.com"},
    )

    # wildcard_hostname_acls returns domains with leading dot (stripped of * only)
    assert backend.wildcard_hostname_acls == {".example.com", ".test.com"}
    # standard_hostname_acls returns non-wildcard hostnames (empty in this case)
    assert backend.standard_hostname_acls == set()


def test_haproxy_route_backend_only_standard_hostnames(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HAProxyRouteBackend with only standard (non-wildcard) hostnames.
    act: Get wildcard_hostname_acls and standard_hostname_acls properties.
    assert: wildcard_hostname_acls is empty, standard_hostname_acls contains the hostnames.
    """
    requirer_data = haproxy_route_relation_data("test_service", relation_id=1)
    backend = HAProxyRouteBackend(
        relation_id=1,
        application_data=requirer_data.application_data,
        servers=[
            HAProxyRouteServer(
                server_name="test-0",
                address=IPv4Address("10.0.0.1"),
                port=80,
                protocol="http",
                check=None,
                maxconn=None,
            )
        ],
        hostname_acls={"example.com", "test.example.com"},
    )

    # No wildcard hostnames, so wildcard_hostname_acls is empty
    assert backend.wildcard_hostname_acls == set()
    # standard_hostname_acls returns the non-wildcard hostnames
    assert backend.standard_hostname_acls == {"example.com", "test.example.com"}


def test_haproxy_route_backend_no_hostnames(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HAProxyRouteBackend with no hostnames.
    act: Get wildcard_hostname_acls and standard_hostname_acls properties.
    assert: Both properties return empty sets.
    """
    requirer_data = haproxy_route_relation_data("test_service", relation_id=1)
    backend = HAProxyRouteBackend(
        relation_id=1,
        application_data=requirer_data.application_data,
        servers=[
            HAProxyRouteServer(
                server_name="test-0",
                address=IPv4Address("10.0.0.1"),
                port=80,
                protocol="http",
                check=None,
                maxconn=None,
            )
        ],
        hostname_acls=set(),
    )

    assert backend.wildcard_hostname_acls == set()
    assert backend.standard_hostname_acls == set()


def test_generate_hostname_acls_with_wildcard_hostname(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create requirer data with wildcard hostname.
    act: Call generate_hostname_acls.
    assert: Returns the wildcard hostname.
    """
    requirer_data = haproxy_route_relation_data(
        "test_service", relation_id=1, hostname="*.example.com"
    )

    hostname_acls = generate_hostname_acls(requirer_data.application_data, None)

    assert hostname_acls == {"*.example.com"}


def test_generate_hostname_acls_with_wildcard_and_additional_hostnames(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create requirer data with wildcard hostname and additional hostnames.
    act: Call generate_hostname_acls.
    assert: Returns all hostnames including wildcards.
    """
    requirer_data = haproxy_route_relation_data(
        "test_service",
        relation_id=1,
        hostname="*.example.com",
        additional_hostnames=["*.test.com", "api.example.com"],
    )

    hostname_acls = generate_hostname_acls(requirer_data.application_data, None)

    assert hostname_acls == {"*.example.com", "*.test.com", "api.example.com"}


def test_generate_hostname_acls_with_external_hostname_and_wildcard(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create requirer data without hostname but with external_hostname.
    act: Call generate_hostname_acls with wildcard external_hostname.
    assert: Returns the external wildcard hostname.
    """
    requirer_data = haproxy_route_relation_data("test_service", relation_id=1)

    hostname_acls = generate_hostname_acls(requirer_data.application_data, "*.haproxy.internal")

    assert hostname_acls == {"*.haproxy.internal"}


def test_haproxy_route_requirers_information_with_wildcard_hostnames(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Setup haproxy-route provider with wildcard hostnames.
    act: Initialize HaproxyRouteRequirersInformation.
    assert: Backends are created with wildcard hostnames properly set.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[],
            relation_ids_with_invalid_data=set(),
        )
    )

    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                haproxy_route_relation_data(
                    "service1",
                    relation_id=1,
                    hostname="*.example.com",
                    additional_hostnames=["api.example.com"],
                ),
                haproxy_route_relation_data(
                    "service2",
                    relation_id=2,
                    hostname="test.com",
                    additional_hostnames=["*.test.com"],
                ),
            ],
            relation_ids_with_invalid_data=set(),
        )
    )

    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname="haproxy.internal",
        peers=[],
        ca_certs_configured=False,
    )

    assert len(haproxy_route_information.backends) == 2

    # Check first backend has wildcard and standard hostname
    backend1 = haproxy_route_information.backends[0]
    assert backend1.hostname_acls == {"*.example.com", "api.example.com"}
    # wildcard_hostname_acls returns domain with leading dot (stripped of * only) from *.example.com
    assert backend1.wildcard_hostname_acls == {".example.com"}
    # standard_hostname_acls returns the non-wildcard hostname
    assert backend1.standard_hostname_acls == {"api.example.com"}

    # Check second backend has both wildcard and standard hostname
    backend2 = haproxy_route_information.backends[1]
    assert backend2.hostname_acls == {"test.com", "*.test.com"}
    # wildcard_hostname_acls returns domain with leading dot (stripped of * only) from *.test.com
    assert backend2.wildcard_hostname_acls == {".test.com"}
    # standard_hostname_acls returns the non-wildcard hostname
    assert backend2.standard_hostname_acls == {"test.com"}


def test_haproxy_route_tcp_frontend_from_backends_single_backend(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create a single TCP backend endpoint.
    act: Call HAProxyRouteTcpFrontend.from_backends with one backend.
    assert: Frontend is created with the backend's settings.
    """
    tcp_backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000,
            backend_port=5000,
            sni="api.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([tcp_backend])

    assert frontend.port == 4000
    assert len(frontend.backends) == 1
    assert frontend.backends[0] == tcp_backend
    assert frontend.enforce_tls is True
    assert frontend.tls_terminate is True
    assert len(frontend.relation_ids_with_invalid_data) == 0


def test_haproxy_route_tcp_frontend_from_backends_multiple_routable(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create multiple TCP backends with enforce_tls=True and SNI set.
    act: Call HAProxyRouteTcpFrontend.from_backends with multiple routable backends.
    assert: Frontend is created with all routable backends merged.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="api2.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2])

    assert frontend.port == 4000
    assert len(frontend.backends) == 2
    assert frontend.backends[0] == backend1
    assert frontend.backends[1] == backend2
    assert frontend.enforce_tls is True
    assert frontend.tls_terminate is True
    assert len(frontend.relation_ids_with_invalid_data) == 0


def test_haproxy_route_tcp_frontend_from_backends_filters_non_routable(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP backends with some missing enforce_tls or SNI.
    act: Call HAProxyRouteTcpFrontend.from_backends with mixed backends.
    assert: Non-routable backends are filtered out and marked as invalid.
    """
    # Routable backend (has enforce_tls=True and SNI)
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    # Non-routable (missing SNI)
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    # Non-routable (enforce_tls=False, no SNI)
    backend3 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=2,
            port=4000,
            enforce_tls=False,
            tls_terminate=True,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2, backend3])

    assert frontend.port == 4000
    assert len(frontend.backends) == 1
    assert frontend.backends[0] == backend1
    assert 1 in frontend.relation_ids_with_invalid_data
    assert 2 in frontend.relation_ids_with_invalid_data


def test_haproxy_route_tcp_frontend_from_backends_prioritizes_tls_terminate(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP backends with some having tls_terminate=True and others False.
    act: Call HAProxyRouteTcpFrontend.from_backends.
    assert: Only backends with tls_terminate=True are used, others marked invalid.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="api2.example.com",
            enforce_tls=True,
            tls_terminate=False,
        )
    )
    backend3 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=2,
            port=4000,
            sni="api3.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2, backend3])

    assert frontend.port == 4000
    assert len(frontend.backends) == 2
    assert backend1 in frontend.backends
    assert backend3 in frontend.backends
    assert backend2 not in frontend.backends
    assert 1 in frontend.relation_ids_with_invalid_data


def test_haproxy_route_tcp_frontend_from_backends_all_tls_terminate_false(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP backends all with tls_terminate=False.
    act: Call HAProxyRouteTcpFrontend.from_backends.
    assert: All backends are kept since none have tls_terminate=True.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=False,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="api2.example.com",
            enforce_tls=True,
            tls_terminate=False,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2])

    assert frontend.port == 4000
    assert len(frontend.backends) == 2
    assert frontend.tls_terminate is False
    assert len(frontend.relation_ids_with_invalid_data) == 0


def test_haproxy_route_tcp_frontend_backend_sni_routing_configurations(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create a frontend with multiple backends with SNI.
    act: Get backend_sni_routing_configurations.
    assert: Returns correct ACL and use_backend configurations for each backend.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="api2.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2])
    routing_configs = frontend.backend_sni_routing_configurations

    assert len(routing_configs) == 2
    assert (
        routing_configs[0].acl == "acl is_tcp-route-requirer_4000 ssl_fc_sni -i api1.example.com"
    )
    assert (
        routing_configs[0].use_backend
        == "use_backend tcp-route-requirer_4000 if is_tcp-route-requirer_4000"
    )
    assert (
        routing_configs[1].acl == "acl is_tcp-route-requirer_4000 ssl_fc_sni -i api2.example.com"
    )
    assert (
        routing_configs[1].use_backend
        == "use_backend tcp-route-requirer_4000 if is_tcp-route-requirer_4000"
    )


def test_haproxy_route_tcp_frontend_is_sni_routing_enabled(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create frontends with and without SNI routing.
    act: Check is_sni_routing_enabled property.
    assert: Returns True when SNI is configured, False otherwise.
    """
    # With SNI
    backend_with_sni = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000,
            sni="api.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    frontend_with_sni = HAProxyRouteTcpFrontend.from_backends([backend_with_sni])
    assert frontend_with_sni.is_sni_routing_enabled is True

    # Without SNI (single backend, no SNI)
    backend_without_sni = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000,
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    frontend_without_sni = HAProxyRouteTcpFrontend.from_backends([backend_without_sni])
    assert frontend_without_sni.is_sni_routing_enabled is False


def test_haproxy_route_tcp_frontend_default_backend_name(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create a frontend on a specific port.
    act: Get default_backend_name.
    assert: Returns correctly formatted default backend name.
    """
    backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(port=4000, enforce_tls=True, tls_terminate=True)
    )
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])

    assert frontend.default_backend_name == "haproxy_route_tcp_4000_default_backend"


def test_haproxy_route_tcp_frontend_content_inspect_delay_required(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create frontends with SNI routing and enforce_tls.
    act: Check content_inspect_delay_required property.
    assert: Returns True when SNI routing or enforce_tls is enabled.
    """
    # With SNI routing
    backend_sni = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000, sni="api.example.com", enforce_tls=True, tls_terminate=True
        )
    )
    frontend_sni = HAProxyRouteTcpFrontend.from_backends([backend_sni])
    assert frontend_sni.content_inspect_delay_required is True

    # With enforce_tls only
    backend_enforce = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(port=4000, enforce_tls=True, tls_terminate=True)
    )
    frontend_enforce = HAProxyRouteTcpFrontend.from_backends([backend_enforce])
    assert frontend_enforce.content_inspect_delay_required is True


def test_haproxy_route_tcp_frontend_enforce_tls_configuration(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create frontends with and without SNI routing.
    act: Get enforce_tls_configuration.
    assert: Returns different reject configurations based on SNI routing.
    """
    # With SNI routing
    backend_sni = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000, sni="api.example.com", enforce_tls=True, tls_terminate=True
        )
    )
    frontend_sni = HAProxyRouteTcpFrontend.from_backends([backend_sni])
    assert frontend_sni.enforce_tls_configuration == "tcp-request content reject"

    # Without SNI routing
    backend_no_sni = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(port=4000, enforce_tls=True, tls_terminate=True)
    )
    frontend_no_sni = HAProxyRouteTcpFrontend.from_backends([backend_no_sni])
    assert (
        frontend_no_sni.enforce_tls_configuration
        == "tcp-request content reject unless { req_ssl_hello_type 1 }"
    )


def test_haproxy_route_tcp_backend_wildcard_sni_property(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create backends with wildcard and standard SNI.
    act: Check is_wildcard_sni and sni_match_rule properties.
    assert: Properties correctly identify and generate match rules for wildcard and standard SNIs.
    """
    # Backend with wildcard SNI
    backend_wildcard = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000, sni="*.example.com", enforce_tls=True, tls_terminate=True
        )
    )
    assert backend_wildcard.is_wildcard_sni is True
    assert backend_wildcard.sni_match_rule == "-m end .example.com"

    # Backend with standard SNI
    backend_standard = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000, sni="api.example.com", enforce_tls=True, tls_terminate=True
        )
    )
    assert backend_standard.is_wildcard_sni is False
    assert backend_standard.sni_match_rule == "-i api.example.com"

    # Backend with no SNI
    backend_no_sni = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(port=4000, enforce_tls=True, tls_terminate=True)
    )
    assert backend_no_sni.is_wildcard_sni is False
    assert backend_no_sni.sni_match_rule is None


def test_haproxy_route_tcp_frontend_wildcard_sni_routing_configurations(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create frontends with wildcard SNI backends.
    act: Check backend_sni_routing_configurations for wildcard ACLs.
    assert: ACLs use -m end for wildcard SNIs.
    """
    # Backend with wildcard SNI
    backend_wildcard = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="*.api.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    frontend = HAProxyRouteTcpFrontend.from_backends([backend_wildcard])
    routing_configs = frontend.backend_sni_routing_configurations

    assert len(routing_configs) == 1
    # Wildcard SNI should use -m end with the leading dot
    assert (
        routing_configs[0].acl
        == "acl is_tcp-route-requirer_4000 ssl_fc_sni -m end .api.example.com"
    )
    assert (
        routing_configs[0].use_backend
        == "use_backend tcp-route-requirer_4000 if is_tcp-route-requirer_4000"
    )


def test_haproxy_route_tcp_frontend_mixed_wildcard_and_standard_sni(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create frontend with both wildcard and standard SNI backends.
    act: Check backend_sni_routing_configurations.
    assert: ACLs correctly use -i for standard and -m end for wildcard SNIs.
    """
    backend_standard = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    backend_wildcard = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="*.test.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend_standard, backend_wildcard])
    routing_configs = frontend.backend_sni_routing_configurations

    assert len(routing_configs) == 2
    # Standard SNI uses -i
    assert routing_configs[0].acl == "acl is_tcp-route-requirer_4000 ssl_fc_sni -i api.example.com"
    # Wildcard SNI uses -m end
    assert routing_configs[1].acl == "acl is_tcp-route-requirer_4000 ssl_fc_sni -m end .test.com"


def test_haproxy_route_tcp_frontend_wildcard_sni_without_tls_terminate(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create frontend with wildcard SNI and tls_terminate=False.
    act: Check backend_sni_routing_configurations.
    assert: ACLs use req.ssl_sni instead of ssl_fc_sni.
    """
    backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="*.example.com",
            enforce_tls=True,
            tls_terminate=False,
        )
    )
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])
    routing_configs = frontend.backend_sni_routing_configurations

    assert len(routing_configs) == 1
    # Should use req.ssl_sni when tls_terminate=False
    assert (
        routing_configs[0].acl == "acl is_tcp-route-requirer_4000 req.ssl_sni -m end .example.com"
    )


def test_parse_haproxy_route_tcp_requirers_data_single_port(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP requirers data with backends on the same port.
    act: Call parse_haproxy_route_tcp_requirers_data.
    assert: Backends are merged into a single frontend.
    """
    requirers_data = HaproxyRouteTcpRequirersData(
        requirers_data=[
            haproxy_route_tcp_relation_data(
                relation_id=0,
                port=4000,
                sni="api1.example.com",
                enforce_tls=True,
                tls_terminate=True,
            ),
            haproxy_route_tcp_relation_data(
                relation_id=1,
                port=4000,
                sni="api2.example.com",
                enforce_tls=True,
                tls_terminate=True,
            ),
        ],
        relation_ids_with_invalid_data=set(),
    )

    frontends = parse_haproxy_route_tcp_requirers_data(requirers_data)

    assert len(frontends) == 1
    assert frontends[0].port == 4000
    assert len(frontends[0].backends) == 2


def test_parse_haproxy_route_tcp_requirers_data_multiple_ports(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP requirers data with backends on different ports.
    act: Call parse_haproxy_route_tcp_requirers_data.
    assert: Each port gets its own frontend.
    """
    requirers_data = HaproxyRouteTcpRequirersData(
        requirers_data=[
            haproxy_route_tcp_relation_data(
                relation_id=0,
                port=4000,
                sni="api1.example.com",
                enforce_tls=True,
                tls_terminate=True,
            ),
            haproxy_route_tcp_relation_data(
                relation_id=1,
                port=5000,
                sni="api2.example.com",
                enforce_tls=True,
                tls_terminate=True,
            ),
            haproxy_route_tcp_relation_data(
                relation_id=2,
                port=4000,
                sni="api3.example.com",
                enforce_tls=True,
                tls_terminate=True,
            ),
        ],
        relation_ids_with_invalid_data=set(),
    )

    frontends = parse_haproxy_route_tcp_requirers_data(requirers_data)

    assert len(frontends) == 2
    ports = {frontend.port for frontend in frontends}
    assert ports == {4000, 5000}

    # Check that port 4000 has 2 backends
    frontend_4000 = next(f for f in frontends if f.port == 4000)
    assert len(frontend_4000.backends) == 2

    # Check that port 5000 has 1 backend
    frontend_5000 = next(f for f in frontends if f.port == 5000)
    assert len(frontend_5000.backends) == 1


def test_parse_haproxy_route_tcp_requirers_data_empty():
    """
    arrange: Create empty TCP requirers data.
    act: Call parse_haproxy_route_tcp_requirers_data.
    assert: Returns empty list of frontends.
    """
    requirers_data = HaproxyRouteTcpRequirersData(
        requirers_data=[],
        relation_ids_with_invalid_data=set(),
    )

    frontends = parse_haproxy_route_tcp_requirers_data(requirers_data)

    assert len(frontends) == 0


def test_haproxy_route_tcp_frontend_all_backends_invalid(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP requirers data with backends on the same port.
    act: Call parse_haproxy_route_tcp_requirers_data.
    assert: Backends are merged into a single frontend.
    """
    backends = [
        HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
            haproxy_route_tcp_relation_data(
                port=4000,
                backend_port=5000,
            )
        ),
        HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
            haproxy_route_tcp_relation_data(
                port=4000,
                backend_port=5000,
            )
        ),
    ]

    with pytest.raises(HAProxyRouteTcpFrontendValidationError):
        HAProxyRouteTcpFrontend.from_backends(backends)


def test_parse_haproxy_route_tcp_requirers_data_all_backends_invalid(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP requirers data with backends on the same port.
    act: Call parse_haproxy_route_tcp_requirers_data.
    assert: Backends are merged into a single frontend.
    """
    requirers_data = HaproxyRouteTcpRequirersData(
        requirers_data=[
            haproxy_route_tcp_relation_data(
                relation_id=0,
                port=4000,
            ),
            haproxy_route_tcp_relation_data(
                relation_id=1,
                port=4000,
            ),
        ],
        relation_ids_with_invalid_data=set(),
    )

    frontends = parse_haproxy_route_tcp_requirers_data(requirers_data)
    assert len(frontends) == 0


def test_haproxy_route_tcp_frontend_default_backend_single_no_sni(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create a frontend with a single backend without SNI.
    act: Get default_backend property.
    assert: Returns the single backend since SNI routing is not enabled.
    """
    backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000,
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])

    assert frontend.default_backend == backend


def test_haproxy_route_tcp_frontend_default_backend_single_with_sni(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create a frontend with a single backend with SNI.
    act: Get default_backend property.
    assert: Returns None since SNI routing is enabled.
    """
    backend = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            port=4000,
            sni="api.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])

    assert frontend.default_backend is None


def test_haproxy_route_tcp_frontend_default_backend_multiple_backends(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create a frontend with multiple backends.
    act: Get default_backend property.
    assert: Returns None since there are multiple backends.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="api2.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2])

    assert frontend.default_backend is None


def test_haproxy_route_tcp_frontend_from_backends_sni_and_plain_tcp(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP backends all with tls_terminate=False.
    act: Call HAProxyRouteTcpFrontend.from_backends.
    assert: All backends are kept since none have tls_terminate=True.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2])

    assert frontend.port == 4000
    assert len(frontend.backends) == 1
    assert len(frontend.relation_ids_with_invalid_data) == 1


def test_haproxy_route_tcp_frontend_from_backends_plain_tcp_multiple_backends(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP backends all with tls_terminate=False.
    act: Call HAProxyRouteTcpFrontend.from_backends.
    assert: All backends are kept since none have tls_terminate=True.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
        )
    )

    with pytest.raises(HAProxyRouteTcpFrontendValidationError):
        HAProxyRouteTcpFrontend.from_backends([backend1, backend2])


def test_haproxy_route_tcp_frontend_from_backends_terminate_and_not_terminate_tls(
    haproxy_route_tcp_relation_data: typing.Callable[..., HaproxyRouteTcpRequirerData],
):
    """
    arrange: Create TCP backends all with tls_terminate=False.
    act: Call HAProxyRouteTcpFrontend.from_backends.
    assert: All backends are kept since none have tls_terminate=True.
    """
    backend1 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=0,
            port=4000,
            sni="api0.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )
    backend2 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=1,
            port=4000,
            sni="api1.example.com",
            enforce_tls=True,
            tls_terminate=True,
        )
    )

    backend3 = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(
        haproxy_route_tcp_relation_data(
            relation_id=2,
            port=4000,
            sni="api2.example.com",
            enforce_tls=True,
            tls_terminate=False,
        )
    )

    frontend = HAProxyRouteTcpFrontend.from_backends([backend1, backend2, backend3])

    assert frontend.port == 4000
    assert len(frontend.backends) == 2
    assert frontend.relation_ids_with_invalid_data == {2}
