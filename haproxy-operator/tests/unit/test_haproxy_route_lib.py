# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route interface library HaproxyRouteRequirerData."""

import ipaddress
import typing
from unittest.mock import MagicMock

import pytest
from charms.haproxy.v0.haproxy_route_tcp import HaproxyRouteTcpRequirersData
from charms.haproxy.v1.haproxy_route import (
    HaproxyRewriteMethod,
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
    RequirerApplicationData,
    RequirerUnitData,
    RewriteConfiguration,
)
from pydantic import ValidationError

from state.haproxy_route import HaproxyRouteRequirersInformation


@pytest.fixture(name="mock_requirer_app_data_with_allow_http")
def mock_requirer_app_data_with_allow_http_fixture():
    """Create mock requirer application data with allow_http enabled."""
    return RequirerApplicationData(
        service="test-service",
        ports=[8080],
        hosts=[ipaddress.ip_address("10.0.0.1")],
        allow_http=True,
    )


@pytest.fixture(name="mock_haproxy_route_requirer_data")
def mock_haproxy_route_requirer_data_fixture():
    """Create mock requirer application data with allow_http enabled."""
    return HaproxyRouteRequirerData(
        relation_id=1,
        application_data=typing.cast(
            RequirerApplicationData,
            RequirerApplicationData.from_dict(
                {
                    "service": "service",
                    "ports": [80],
                    "allow_http": True,
                    "hostname": "example.com",
                    "paths": ["/path"],
                    "deny_paths": ["/private"],
                }
            ),
        ),
        units_data=[
            typing.cast(RequirerUnitData, RequirerUnitData.from_dict({"address": "10.0.0.1"}))
        ],
    )


@pytest.fixture(name="mock_haproxy_route_relation_data")
def mock_haproxy_route_relation_data_fixture(
    mock_haproxy_route_requirer_data: HaproxyRouteRequirerData,
) -> HaproxyRouteRequirersData:
    """Create mock requirer application data with allow_http enabled."""
    return HaproxyRouteRequirersData(
        requirers_data=[mock_haproxy_route_requirer_data],
        relation_ids_with_invalid_data=[],
    )


def test_requirer_application_data_allow_http_default_is_false():
    """
    arrange: Create a RequirerApplicationData model without specifying allow_http.
    act: Check the allow_http value.
    assert: allow_http defaults to False.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
    )

    assert data.allow_http is False


def test_haproxy_route_requirer_data_with_allow_http_true(mock_requirer_app_data_with_allow_http):
    """
    arrange: Create a HaproxyRouteRequirerData with RequirerApplicationData having allow_http=True.
    act: Instantiate HaproxyRouteRequirerData.
    assert: Object is created successfully and allow_http is True.
    """
    requirer_data = HaproxyRouteRequirerData(
        relation_id=2,
        application_data=mock_requirer_app_data_with_allow_http,
        units_data=[RequirerUnitData(address=ipaddress.ip_address("10.0.0.1"))],
    )

    assert requirer_data.application_data.allow_http is True


def test_haproxy_route_requirer_information(
    mock_haproxy_route_relation_data: HaproxyRouteRequirersData,
):
    """
    arrange: Setup all relation providers mock.
    act: Initialize the charm state.
    assert: The proxy mode is correctly set to HAPROXY_ROUTE.
    """
    haproxy_route_tcp_provider_mock = MagicMock()
    haproxy_route_tcp_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteTcpRequirersData(
            requirers_data=[], relation_ids_with_invalid_data=[]
        )
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(return_value=mock_haproxy_route_relation_data)
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        external_hostname=None,
        peers=[],
        ca_certs_configured=False,
    )
    assert haproxy_route_information.acls_for_allow_http == [
        "{ req.hdr(Host) -m str example.com } { path_beg -i /path } !{ path_beg -i /private }"
    ]


def test_rewrite_expression_does_not_allow_newline():
    """
    act: Create a RewriteConfiguration with an expression containing a newline character.
    assert: ValidationError is raised
    """
    with pytest.raises(ValidationError) as exc:
        RewriteConfiguration(
            method=HaproxyRewriteMethod.SET_PATH,
            expression="data\ninjection data",
        )
    assert "invalid character" in str(exc)


def test_check_external_grpc_port_with_https(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HaproxyRouteRequirersData with external_grpc_port and https protocol.
    act: Instantiate HaproxyRouteRequirersData.
    assert: relation_ids_with_invalid_data is empty.
    """
    requirer_data = haproxy_route_relation_data(
        "grpc-service",
        protocol="https",
        external_grpc_port=9000,
    )

    data = HaproxyRouteRequirersData(
        requirers_data=[requirer_data],
        relation_ids_with_invalid_data=[],
    )

    assert data.relation_ids_with_invalid_data == []


def test_check_external_grpc_port_with_http_invalid(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HaproxyRouteRequirersData with external_grpc_port and http protocol.
    act: Instantiate HaproxyRouteRequirersData.
    assert: relation_ids_with_invalid_data contains the relation_id.
    """
    relation_id = 1
    requirer_data = haproxy_route_relation_data(
        "grpc-service",
        relation_id=relation_id,
        protocol="http",
        external_grpc_port=9000,
    )

    data = HaproxyRouteRequirersData(
        requirers_data=[requirer_data],
        relation_ids_with_invalid_data=[],
    )

    assert data.relation_ids_with_invalid_data == [relation_id]


def test_check_external_grpc_port_unique(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HaproxyRouteRequirersData with various gRPC port scenarios.
    act: Instantiate HaproxyRouteRequirersData.
    assert: relation_ids_with_invalid_data contains only relations with duplicate ports.

    Test cases covered:
    - Services with unique gRPC ports (should pass)
    - Services with duplicate ports (should be marked invalid)
    - Services without gRPC port specified (should be ignored)
    """
    # rel_id=1,2,5: port 9000 (duplicate - all should be invalid)
    # rel_id=3,4: port 9001 (duplicate - all should be invalid)
    # rel_id=6: port 9002 (unique - should be valid)
    # rel_id=7,8: no port specified (should be ignored)
    requirer_data_1 = haproxy_route_relation_data(
        "grpc-service-1",
        relation_id=1,
        protocol="https",
        external_grpc_port=9000,
    )
    requirer_data_2 = haproxy_route_relation_data(
        "grpc-service-2",
        relation_id=2,
        protocol="https",
        external_grpc_port=9000,
    )
    requirer_data_3 = haproxy_route_relation_data(
        "grpc-service-3",
        relation_id=3,
        protocol="https",
        external_grpc_port=9001,
    )
    requirer_data_4 = haproxy_route_relation_data(
        "grpc-service-4",
        relation_id=4,
        protocol="https",
        external_grpc_port=9001,
    )
    requirer_data_5 = haproxy_route_relation_data(
        "grpc-service-5",
        relation_id=5,
        protocol="https",
        external_grpc_port=9000,
    )
    requirer_data_6 = haproxy_route_relation_data(
        "grpc-service-6",
        relation_id=6,
        protocol="https",
        external_grpc_port=9002,
    )
    requirer_data_7 = haproxy_route_relation_data(
        "http-service-1",
        relation_id=7,
        protocol="https",
    )
    requirer_data_8 = haproxy_route_relation_data(
        "http-service-2",
        relation_id=8,
        protocol="https",
    )

    data = HaproxyRouteRequirersData(
        requirers_data=[
            requirer_data_1,
            requirer_data_2,
            requirer_data_3,
            requirer_data_4,
            requirer_data_5,
            requirer_data_6,
            requirer_data_7,
            requirer_data_8,
        ],
        relation_ids_with_invalid_data=[],
    )

    assert set(data.relation_ids_with_invalid_data) == {1, 2, 3, 4, 5}
