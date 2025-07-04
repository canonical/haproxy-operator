# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route relation."""

import pytest
from charms.haproxy.v0.haproxy_route import (
    LoadBalancingAlgorithm,
    RequirerApplicationData,
    RequirerUnitData,
    ServerHealthCheck,
)
from ops.testing import Harness

from state.haproxy_route import (
    HaproxyRouteIntegrationDataValidationError,
    HaproxyRouteRequirersInformation,
)

MOCK_EXTERNAL_HOSTNAME = "haproxy.internal"


@pytest.fixture(name="requirer_application_data")
def requirer_application_data_fixture():
    """Create sample requirer data for testing."""
    return RequirerApplicationData(
        service="test-service",
        ports=[8080, 8443],
        paths=["/api/v1", "/api/v2"],
        subdomains=["api"],
        check=ServerHealthCheck(path="/health"),
        server_maxconn=100,
        load_balancing={"algorithm": LoadBalancingAlgorithm.ROUNDROBIN},
    ).dump()


@pytest.fixture(name="extra_requirer_application_data")
def extra_requirer_application_data_fixture():
    """Create sample requirer data for testing."""
    return RequirerApplicationData(
        service="test-service-extra",
        ports=[9000],
        paths=[],
        subdomains=["extra"],
        check=ServerHealthCheck(path="/extra"),
        server_maxconn=100,
        load_balancing={"algorithm": LoadBalancingAlgorithm.COOKIE, "cookie": "Host"},
    ).dump()


def generate_unit_data(unit_address):
    """Generate unit data.

    Args:
        unit_address: The unit address.

    Returns:
        RequirerUnitData: databag content with the given unit address.
    """
    return RequirerUnitData(address=unit_address).dump()


@pytest.fixture(name="haproxy_peer_units_address")
def haproxy_peer_units_address_fixture() -> list[str]:
    """Mock list of haproxy peer units address"""
    return ["10.0.0.100", "10.0.0.101"]


def test_haproxy_route_from_provider(
    harness: Harness,
    requirer_application_data,
    extra_requirer_application_data,
    haproxy_peer_units_address,
):
    """
    arrange: Given a charm with haproxy route relation established.
    act: Initialize HaproxyRouteRequirersInformation state component.
    assert: The state component is initialized correctly with expected data.
    """
    relation_id = harness.add_relation(
        "haproxy-route",
        "requirer-charm",
        app_data=requirer_application_data,
    )

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(relation_id, "requirer-charm/0", generate_unit_data("10.0.0.1"))
    harness.add_relation_unit(relation_id, "requirer-charm/1")
    harness.update_relation_data(relation_id, "requirer-charm/1", generate_unit_data("10.0.0.2"))

    extra_relation_id = harness.add_relation(
        "haproxy-route",
        "extra-requirer-charm",
        app_data=extra_requirer_application_data,
    )
    harness.add_relation_unit(extra_relation_id, "extra-requirer-charm/0")
    harness.update_relation_data(
        extra_relation_id, "extra-requirer-charm/0", generate_unit_data("10.0.0.3")
    )

    harness.begin()
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        harness.charm.haproxy_route_provider, MOCK_EXTERNAL_HOSTNAME, haproxy_peer_units_address
    )

    assert len(haproxy_route_information.backends) == 2
    backend = haproxy_route_information.backends[0]
    assert backend.relation_id == relation_id
    assert backend.external_hostname == MOCK_EXTERNAL_HOSTNAME
    assert backend.backend_name == "test-service"
    assert len(backend.servers) == 4

    assert backend.hostname_acls == [f"api.{MOCK_EXTERNAL_HOSTNAME}"]
    assert backend.path_acl_required is True

    extra_backend = haproxy_route_information.backends[1]
    assert extra_backend.relation_id == extra_relation_id
    assert extra_backend.external_hostname == MOCK_EXTERNAL_HOSTNAME
    assert extra_backend.backend_name == "test-service-extra"
    assert len(extra_backend.servers) == 1
    assert extra_backend.hostname_acls == [f"extra.{MOCK_EXTERNAL_HOSTNAME}"]
    assert extra_backend.path_acl_required is False

    assert len(haproxy_route_information.peers) == 2


def test_haproxy_route_from_provider_duplicate_backend_names(
    harness: Harness,
    requirer_application_data,
):
    """
    arrange: Given a charm with multiple haproxy route relations with duplicate backend names.
    act: Initialize HaproxyRouteRequirersInformation state component.
    assert: HaproxyRouteIntegrationDataValidationError is raised.
    """
    relation_id = harness.add_relation(
        "haproxy-route",
        "requirer-charm",
        app_data=requirer_application_data,
    )

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(relation_id, "requirer-charm/0", generate_unit_data("10.0.0.1"))
    harness.add_relation_unit(relation_id, "requirer-charm/1")
    harness.update_relation_data(relation_id, "requirer-charm/1", generate_unit_data("10.0.0.2"))

    extra_relation_id = harness.add_relation(
        "haproxy-route",
        "extra-requirer-charm",
        app_data=requirer_application_data,
    )
    harness.add_relation_unit(extra_relation_id, "extra-requirer-charm/0")
    harness.update_relation_data(
        extra_relation_id, "extra-requirer-charm/0", generate_unit_data("10.0.0.3")
    )

    harness.begin()
    # Act & Assert
    with pytest.raises(HaproxyRouteIntegrationDataValidationError):
        HaproxyRouteRequirersInformation.from_provider(
            haproxy_route=harness.charm.haproxy_route_provider,
            external_hostname=MOCK_EXTERNAL_HOSTNAME,
            peers=[],
        )
