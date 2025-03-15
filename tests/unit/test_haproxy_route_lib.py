# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route interface library."""

import json
import logging
from typing import Any
from unittest.mock import MagicMock

import ops
import pytest
from charms.haproxy.v0.haproxy_route import (
    DataValidationError,
    HaproxyRouteProviderAppData,
    HaproxyRouteRequirer,
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
    LoadBalancingAlgorithm,
    RequirerApplicationData,
    RequirerUnitData,
    ServerHealthCheck,
)
from ops.testing import Harness
from pydantic import ValidationError

logger = logging.getLogger()
MOCK_RELATION_NAME = "haproxy-route"
MOCK_ADDRESS = "10.0.0.1"


@pytest.fixture(name="mock_relation_data")
def mock_relation_data_fixture():
    """Create mock relation data."""
    return {
        "service": "test-service",
        "ports": [8080],
        "paths": ["/api"],
        "subdomains": ["api"],
        "load_balancing": {"algorithm": "leastconn"},
        "check": {"interval": 60, "rise": 2, "fall": 3, "path": "/health"},
    }


@pytest.fixture(name="mock_unit_data")
def mock_unit_data_fixture():
    """Create mock unit data."""
    return {"address": MOCK_ADDRESS}


@pytest.fixture(name="mock_provider_app_data")
def mock_provider_app_data_fixture():
    """Create mock unit data."""
    return HaproxyRouteProviderAppData(endpoints=["https://backend.haproxy.internal/path"]).dump()


def test_requirer_application_data_validation():
    """
    arrange: Create a RequirerApplicationData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        paths=["/api"],
        subdomains=["api"],
        check=ServerHealthCheck(path="/health"),
        load_balancing={"algorithm": LoadBalancingAlgorithm.LEASTCONN},
    )

    assert data.service == "test-service"
    assert data.ports == [8080]
    assert data.paths == ["/api"]
    assert data.subdomains == ["api"]
    assert data.check.path == "/health"  # pylint: disable=no-member
    # pylint: disable=no-member
    assert data.load_balancing.algorithm == LoadBalancingAlgorithm.LEASTCONN


def test_requirer_application_data_cookie_validation():
    """
    arrange: Create a RequirerApplicationData model with COOKIE load balancing without cookie set.
    act: Validate the model.
    assert: Validation raises an error.
    """
    with pytest.raises(ValidationError):
        RequirerApplicationData(
            service="test-service",
            ports=[8080],
            load_balancing={"algorithm": LoadBalancingAlgorithm.COOKIE},
        )


def test_requirer_application_data_cookie_valid():
    """
    arrange: Create a RequirerApplicationData model with COOKIE load balancing algorithm
        and cookie set.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        load_balancing={"algorithm": LoadBalancingAlgorithm.COOKIE, "cookie": "JSESSIONID"},
    )

    # pylint: disable=no-member
    assert data.load_balancing.algorithm == LoadBalancingAlgorithm.COOKIE
    assert data.load_balancing.cookie == "JSESSIONID"  # pylint: disable=no-member


def test_requirer_unit_data_validation():
    """
    arrange: Create a RequirerUnitData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = RequirerUnitData(address=MOCK_ADDRESS)
    assert str(data.address) == MOCK_ADDRESS


def test_provider_app_data_validation():
    """
    arrange: Create a HaproxyRouteProviderAppData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = HaproxyRouteProviderAppData(endpoints=["https://example.com"])
    # Note: pydantic automatically adds a trailing slash '/'
    # after validating the URL, this is intended behavior but we need to keep this in mind
    # in case where this might cause problems.
    assert [str(endpoint) for endpoint in data.endpoints] == ["https://example.com/"]


def test_requirers_data_duplicate_services():
    """
    arrange: Create HaproxyRouteRequirersData with duplicate service names.
    act: Validate the model.
    assert: Validation raises an error.
    """
    app_data1 = RequirerApplicationData(
        service="test-service",
        ports=[8080],
    )
    app_data2 = RequirerApplicationData(
        service="test-service",  # Same service name
        ports=[9090],
    )

    requirer_data1 = HaproxyRouteRequirerData(
        relation_id=1,
        application_data=app_data1,
        units_data=[RequirerUnitData(address=MOCK_ADDRESS)],
    )

    requirer_data2 = HaproxyRouteRequirerData(
        relation_id=2,
        application_data=app_data2,
        units_data=[RequirerUnitData(address="10.0.0.2")],
    )

    with pytest.raises(DataValidationError):
        HaproxyRouteRequirersData(requirers_data=[requirer_data1, requirer_data2])


def test_load_requirer_application_data(mock_relation_data):
    """
    arrange: Create a databag with valid application data.
    act: Load the data with RequirerApplicationData.load().
    assert: Data is loaded correctly.
    """
    databag = {k: json.dumps(v) for k, v in mock_relation_data.items()}
    data = RequirerApplicationData.load(databag)

    assert data.service == "test-service"
    assert data.ports == [8080]
    assert data.paths == ["/api"]
    assert data.subdomains == ["api"]
    assert data.check.interval == 60
    assert data.check.rise == 2
    assert data.check.fall == 3
    assert data.check.path == "/health"


def test_dump_requirer_application_data():
    """
    arrange: Create a RequirerApplicationData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        paths=["/api"],
        subdomains=["api"],
        check=ServerHealthCheck(path="/health"),
    )

    databag: dict[str, Any] = {}
    data.dump(databag)

    assert "service" in databag
    assert json.loads(databag["service"]) == "test-service"
    assert json.loads(databag["ports"]) == [8080]
    assert json.loads(databag["paths"]) == ["/api"]
    assert json.loads(databag["subdomains"]) == ["api"]
    assert json.loads(databag["check"])["path"] == "/health"


def test_load_requirer_unit_data(mock_unit_data):
    """
    arrange: Create a databag with valid unit data.
    act: Load the data with RequirerUnitData.load().
    assert: Data is loaded correctly.
    """
    databag = {k: json.dumps(v) for k, v in mock_unit_data.items()}
    data = RequirerUnitData.load(databag)

    assert str(data.address) == MOCK_ADDRESS


def test_dump_requirer_unit_data():
    """
    arrange: Create a RequirerUnitData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    data = RequirerUnitData(address=MOCK_ADDRESS)

    databag: dict[str, str] = {}
    data.dump(databag)

    assert "address" in databag
    assert json.loads(databag["address"]) == MOCK_ADDRESS


def test_haproxy_route_provider_initialization(harness):
    """
    arrange: Create a harness with a charm that has a HaproxyRouteProvider.
    act: Initialize the harness.
    assert: HaproxyRouteProvider is initialized correctly.
    """
    harness.begin()
    # pylint: disable=protected-access
    assert harness.charm.haproxy_route_provider._relation_name == MOCK_RELATION_NAME


def test_provide_haproxy_route_requirements(mock_relation_data):
    """Test that providing haproxy route requirements updates application data correctly."""
    requirer_charm = MagicMock(prototype=ops.CharmBase)
    requirer_charm.unit.is_leader = lambda: True

    relation_mock = MagicMock()
    relation_data_mock = MagicMock()
    relation_mock.data.__getitem__ = MagicMock(return_value=relation_data_mock)

    requirer = HaproxyRouteRequirer(charm=requirer_charm, relation_name=MOCK_RELATION_NAME)
    requirer.relation = relation_mock

    # Update the requirements
    requirer.provide_haproxy_route_requirements(
        service=mock_relation_data["service"],
        ports=mock_relation_data["ports"],
        paths=mock_relation_data["paths"],
        subdomains=mock_relation_data["subdomains"],
        unit_address="10.0.1.0",
    )

    assert relation_data_mock.update.call_count == 2


def test_update_relation_data_non_leader(mock_relation_data):
    """Test that unit data is updated but app data is not when not the leader."""
    requirer_charm = MagicMock(prototype=ops.CharmBase)
    requirer_charm.unit.is_leader = lambda: False

    relation_mock = MagicMock()
    relation_data_mock = MagicMock()
    relation_mock.data.__getitem__ = MagicMock(return_value=relation_data_mock)

    requirer = HaproxyRouteRequirer(charm=requirer_charm, relation_name=MOCK_RELATION_NAME)
    requirer.relation = relation_mock

    # Update the requirements
    requirer.provide_haproxy_route_requirements(
        service=mock_relation_data["service"],
        ports=mock_relation_data["ports"],
        paths=mock_relation_data["paths"],
        subdomains=mock_relation_data["subdomains"],
        unit_address="10.0.1.0",
    )

    relation_data_mock.update.assert_called_once()


def test_get_proxied_endpoints(harness: Harness, mock_provider_app_data):
    """Test that get_proxied_endpoints returns the endpoints correctly."""
    harness.add_relation("haproxy-route", "provider-app", app_data=mock_provider_app_data)
    harness.begin()
    requirer = HaproxyRouteRequirer(charm=harness.charm, relation_name=MOCK_RELATION_NAME)

    endpoints = requirer.get_proxied_endpoints()
    assert len(endpoints) == 1
    assert str(endpoints[0]) == json.loads(mock_provider_app_data["endpoints"])[0]


def test_get_proxied_endpoints_empty_data(harness: Harness):
    """Test that get_proxied_endpoints returns empty list when no data."""
    harness.add_relation("haproxy-route", "provider-app")
    harness.begin()
    requirer = HaproxyRouteRequirer(charm=harness.charm, relation_name=MOCK_RELATION_NAME)

    endpoints = requirer.get_proxied_endpoints()
    assert endpoints == []


def test_get_proxied_endpoints_invalid_data(harness: Harness):
    """Test that get_proxied_endpoints handles invalid data gracefully."""
    harness.add_relation(
        "haproxy-route",
        "provider-app",
        app_data={"endpoints": json.dumps(["invalid"])},
    )
    harness.begin()
    requirer = HaproxyRouteRequirer(charm=harness.charm, relation_name=MOCK_RELATION_NAME)

    endpoints = requirer.get_proxied_endpoints()
    assert endpoints == []


def test_prepare_unit_data_no_address(harness: Harness):
    """Test that DataValidationError is raised when no address is available."""
    harness.begin()
    requirer = HaproxyRouteRequirer(charm=harness.charm, relation_name=MOCK_RELATION_NAME)

    # Reset the unit address and mock a binding with no address
    requirer.charm.model.get_binding = MagicMock(return_value=None)

    with pytest.raises(DataValidationError):
        # We want to specifically test this method.
        requirer._prepare_unit_data()  # pylint: disable=protected-access
