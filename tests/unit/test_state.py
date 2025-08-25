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
    TcpRequirerApplicationData,
    TcpRequirerUnitData,
)
from charms.haproxy.v1.haproxy_route import (
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
    RequirerApplicationData,
    RequirerUnitData,
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


@pytest.fixture(scope="module", name="haproxy_route_tcp_relation_data")
def haproxy_route_tcp_relation_data_fixture() -> (
    typing.Callable[[int], HaproxyRouteTcpRequirersData]
):
    """Mock systemd lib methods."""

    def generate_requirer_data(port: int) -> HaproxyRouteTcpRequirersData:
        """Generate haproxy-route-tcp relation data with custom port.

        Args:
            port: Port included in the relation data.

        Returns:
            HaproxyRouteTcpRequirersData: Generated relation data.
        """
        return HaproxyRouteTcpRequirersData(
            requirers_data=[
                HaproxyRouteTcpRequirerData(
                    relation_id=0,
                    application="tcp-route-requirer",
                    application_data=typing.cast(
                        TcpRequirerApplicationData,
                        TcpRequirerApplicationData.from_dict({"port": port}),
                    ),
                    units_data=[
                        typing.cast(
                            TcpRequirerUnitData,
                            TcpRequirerUnitData.from_dict({"address": "10.0.0.1"}),
                        )
                    ],
                )
            ],
            relation_ids_with_invalid_data=[],
        )

    return generate_requirer_data


@pytest.fixture(scope="module", name="haproxy_route_relation_data")
def haproxy_route_relation_data_fixture() -> HaproxyRouteRequirersData:
    """Mock systemd lib methods."""
    return HaproxyRouteRequirersData(
        requirers_data=[
            HaproxyRouteRequirerData(
                relation_id=1,
                application_data=typing.cast(
                    RequirerApplicationData,
                    RequirerApplicationData.from_dict({"service": "test", "ports": [80]}),
                ),
                units_data=[
                    typing.cast(
                        RequirerUnitData, RequirerUnitData.from_dict({"address": "10.0.0.1"})
                    )
                ],
            )
        ],
        relation_ids_with_invalid_data=[],
    )


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
    haproxy_route_tcp_relation_data: typing.Callable[[int], HaproxyRouteTcpRequirersData],
    haproxy_route_relation_data: HaproxyRouteRequirersData,
):
    """
    arrange: Setup mock haproxy-route and haproxy-route-tcp relation providers.
    act: Initialize the HaproxyRouteRequirersInformation state.
    assert: TCP endpoints are not parsed because port 80 is not allowed.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=haproxy_route_tcp_relation_data(80)
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(return_value=haproxy_route_relation_data)
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname=None,
        peers=[],
    )
    assert not haproxy_route_information.tcp_endpoints
    assert len(haproxy_route_information.relation_ids_with_invalid_data_tcp) == 1


def test_haproxy_route_requirer_information(
    haproxy_route_tcp_relation_data: typing.Callable[[int], HaproxyRouteTcpRequirersData],
    haproxy_route_relation_data: HaproxyRouteRequirersData,
):
    """
    arrange: Setup all relation providers mock.
    act: Initialize the charm state.
    assert: The proxy mode is correctly set to HAPROXY_ROUTE.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=haproxy_route_tcp_relation_data(4000)
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(return_value=haproxy_route_relation_data)
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname=None,
        peers=[],
    )
    assert len(haproxy_route_information.tcp_endpoints) == 1


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
    haproxy_route_tcp_relation_data: typing.Callable[[int], HaproxyRouteTcpRequirersData],
):
    """
    arrange: Generate TCP relation data.
    act: Initialize the HAProxyRouteTcpEndpoint class with the generated relation data.
    assert: The class correctly parses the information.
    """
    haproxy_route_tcp: HaproxyRouteTcpRequirerData = haproxy_route_tcp_relation_data(
        4000
    ).requirers_data[0]
    tcp_endpoint = HAProxyRouteTcpEndpoint.from_haproxy_route_tcp_requirer_data(haproxy_route_tcp)
    assert tcp_endpoint.relation_id == haproxy_route_tcp.relation_id
    assert tcp_endpoint.application == haproxy_route_tcp.application
    assert tcp_endpoint.servers[0].address == haproxy_route_tcp.units_data[0].address
    assert tcp_endpoint.servers[0].server_name == f"{haproxy_route_tcp.application}-0"
    assert tcp_endpoint.servers[0].port == haproxy_route_tcp.application_data.backend_port
