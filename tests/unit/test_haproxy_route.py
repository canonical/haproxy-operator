# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route interface library HaproxyRouteRequirerData."""

import typing
from unittest.mock import MagicMock

import pytest
from charms.haproxy.v0.haproxy_route_tcp import HaproxyRouteTcpRequirersData
from charms.haproxy.v1.haproxy_route import (
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
    RequirerApplicationData,
    RequirerUnitData,
)

from state.haproxy_route import HaproxyRouteRequirersInformation


@pytest.fixture(name="mock_requirer_app_data_with_allow_http")
def mock_requirer_app_data_with_allow_http_fixture():
    """Create mock requirer application data with allow_http enabled."""
    return RequirerApplicationData(
        service="test-service",
        ports=[8080],
        hosts=["10.0.0.1"],
        allow_http=True,
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
        units_data=[RequirerUnitData(address="10.0.0.1")],
    )

    assert requirer_data.application_data.allow_http is True


def test_haproxy_route_requirer_information():
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
    mock_hostname = "example.com"
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(
        return_value=HaproxyRouteRequirersData(
            requirers_data=[
                HaproxyRouteRequirerData(
                    relation_id=1,
                    application_data=typing.cast(
                        RequirerApplicationData,
                        RequirerApplicationData.from_dict(
                            {
                                "service": "service",
                                "ports": [80],
                                "allow_http": True,
                                "hostname": mock_hostname,
                                "paths": ["/path"],
                                "deny_paths": ["/private"],
                            }
                        ),
                    ),
                    units_data=[
                        typing.cast(
                            RequirerUnitData, RequirerUnitData.from_dict({"address": "10.0.0.1"})
                        )
                    ],
                ),
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
    assert haproxy_route_information.allow_http_acls == [
        f"{{ req.hdr(Host) -m str {mock_hostname} }} "
        "{ path_beg -i /path } !{ path_beg -i /private }"
    ]
