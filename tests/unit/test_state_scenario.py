# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route relation."""

import pytest
from charms.haproxy.v1.haproxy_route import (
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
from state.ingress import IngressIntegrationDataValidationError, IngressRequirersInformation
from state.ingress_per_unit import (
    IngressPerUnitIntegrationDataValidationError,
    IngressPerUnitRequirersInformation,
)

MOCK_EXTERNAL_HOSTNAME = "haproxy.internal"


@pytest.fixture(name="haproxy_requirer_application_data")
def haproxy_requirer_application_data_fixture():
    """Create sample haproxy requirer data for testing."""
    return RequirerApplicationData(
        service="test-service",
        ports=[8080, 8443],
        paths=["/api/v1", "/api/v2"],
        hostname="api.haproxy.internal",
        check=ServerHealthCheck(path="/health"),
        server_maxconn=100,
        load_balancing={"algorithm": LoadBalancingAlgorithm.ROUNDROBIN},
    ).dump()


@pytest.fixture(name="extra_haproxy_requirer_application_data")
def extra_haproxy_requirer_application_data_fixture():
    """Create sample haproxy requirer data for testing."""
    return RequirerApplicationData(
        service="test-service-extra",
        ports=[9000],
        hosts=["10.0.0.1", "10.0.0.2"],
        paths=[],
        hostname="extra.haproxy.internal",
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
    haproxy_requirer_application_data,
    extra_haproxy_requirer_application_data,
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
        app_data=haproxy_requirer_application_data,
    )

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(relation_id, "requirer-charm/0", generate_unit_data("10.0.0.1"))
    harness.add_relation_unit(relation_id, "requirer-charm/1")
    harness.update_relation_data(relation_id, "requirer-charm/1", generate_unit_data("10.0.0.2"))

    extra_relation_id = harness.add_relation(
        "haproxy-route",
        "extra-requirer-charm",
        app_data=extra_haproxy_requirer_application_data,
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
    assert len(extra_backend.servers) == 2
    assert extra_backend.hostname_acls == [f"extra.{MOCK_EXTERNAL_HOSTNAME}"]
    assert extra_backend.path_acl_required is False

    assert len(haproxy_route_information.peers) == 2


def test_haproxy_route_from_provider_duplicate_backend_names(
    harness: Harness,
    haproxy_requirer_application_data,
):
    """
    arrange: Given a charm with multiple haproxy route relations with duplicate backend names.
    act: Initialize HaproxyRouteRequirersInformation state component.
    assert: HaproxyRouteIntegrationDataValidationError is raised.
    """
    relation_id = harness.add_relation(
        "haproxy-route",
        "requirer-charm",
        app_data=haproxy_requirer_application_data,
    )

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(relation_id, "requirer-charm/0", generate_unit_data("10.0.0.1"))
    harness.add_relation_unit(relation_id, "requirer-charm/1")
    harness.update_relation_data(relation_id, "requirer-charm/1", generate_unit_data("10.0.0.2"))

    extra_relation_id = harness.add_relation(
        "haproxy-route",
        "extra-requirer-charm",
        app_data=haproxy_requirer_application_data,
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


def test_ingress_per_unit_from_provider(harness: Harness):
    """
    arrange: Setup ingress-per-unit requirer charm with two remote units integrated with haproxy.
    act: Initialize the IngressPerUnitRequirersInformation.
    assert: The state component is initialized correctly with expected data.
    """
    harness.begin()

    relation_id = harness.add_relation("ingress-per-unit", "requirer-charm")

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(
        relation_id,
        "requirer-charm/0",
        {
            "host": "juju-unit1.lxd",
            "port": "80",
            "model": "test",
            "name": "requirer-charm/0",
        },
    )

    harness.add_relation_unit(relation_id, "requirer-charm/1")
    harness.update_relation_data(
        relation_id,
        "requirer-charm/1",
        {
            "host": "juju-unit2.lxd",
            "port": "80",
            "model": "test",
            "name": "requirer-charm/1",
        },
    )

    ingress_per_unit = IngressPerUnitRequirersInformation.from_provider(
        harness.charm._ingress_per_unit_provider  # pylint: disable=protected-access
    )

    backends = ingress_per_unit.backends
    assert len(backends) == 2
    hostnames = [backend.hostname_or_ip for backend in backends]
    assert "juju-unit1.lxd" in hostnames
    assert "juju-unit2.lxd" in hostnames
    ports = [backend.port for backend in backends]
    assert ports == [80, 80]
    backend_names = [backend.backend_name for backend in backends]
    assert "test_requirer-charm_0" in backend_names
    assert "test_requirer-charm_1" in backend_names
    backend_paths = [backend.backend_path for backend in backends]
    assert "test-requirer-charm/0" in backend_paths
    assert "test-requirer-charm/1" in backend_paths


def test_ingress_per_unit_from_provider_validation_error(harness: Harness):
    """
    arrange: Setup ingress-per-unit requirer charm with invalid data.
    act: Initialize the IngressPerUnitRequirersInformation.
    assert: IngressPerUnitIntegrationDataValidationError is raised.
    """
    relation_id = harness.add_relation("ingress-per-unit", "requirer-charm")

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(
        relation_id,
        "requirer-charm/0",
        {
            "host": "juju-unit1.lxd",
            "port": "invalid_port",
            "model": "test",
            "name": "requirer-charm/0",
        },
    )

    harness.begin()

    with pytest.raises(IngressPerUnitIntegrationDataValidationError):
        IngressPerUnitRequirersInformation.from_provider(
            harness.charm._ingress_per_unit_provider  # pylint: disable=protected-access
        )


def test_ingress_from_provider_validation_error(harness: Harness):
    """
    arrange: Setup ingress requirer charm with invalid data.
    act: Initialize the IngressRequirersInformation.
    assert: IngressIntegrationDataValidationError is raised.
    """
    relation_id = harness.add_relation("ingress", "requirer-charm")

    harness.add_relation_unit(relation_id, "requirer-charm/0")
    harness.update_relation_data(
        relation_id,
        "requirer-charm",
        {},
    )

    harness.begin()

    with pytest.raises(IngressIntegrationDataValidationError):
        IngressRequirersInformation.from_provider(
            harness.charm._ingress_provider  # pylint: disable=protected-access
        )
