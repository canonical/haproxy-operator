# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route interface library HaproxyRouteRequirerData."""

import ipaddress
import json
import typing
from ipaddress import IPv4Address
from unittest.mock import MagicMock

import pytest
from charms.haproxy.v1.haproxy_route_tcp import HaproxyRouteTcpRequirersData
from charms.haproxy.v2.haproxy_route import (
    DataValidationError,
    HaproxyRewriteMethod,
    HaproxyRouteProvider,
    HaproxyRouteProviderAppData,
    HaproxyRouteRequirer,
    HaproxyRouteRequirerData,
    HaproxyRouteRequirersData,
    LoadBalancingAlgorithm,
    LoadBalancingConfiguration,
    RequirerApplicationData,
    RequirerUnitData,
    RewriteConfiguration,
    ServerHealthCheck,
)
from pydantic import ValidationError

from state.haproxy_route import HaproxyRouteRequirersInformation

MOCK_RELATION_NAME = "haproxy-route"
MOCK_ADDRESS = "10.0.0.1"


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
        relation_ids_with_invalid_data=set(),
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
            requirers_data=[], relation_ids_with_invalid_data=set()
        )
    )
    haproxy_route_provider_mock = MagicMock()
    haproxy_route_provider_mock.get_data = MagicMock(return_value=mock_haproxy_route_relation_data)
    haproxy_route_information = HaproxyRouteRequirersInformation.from_provider(
        haproxy_route=haproxy_route_provider_mock,
        haproxy_route_tcp=haproxy_route_tcp_provider_mock,
        haproxy_route_policy=MagicMock(relation=None),
        external_hostname=None,
        peers=[],
        ca_certs_configured=False,
    )
    assert haproxy_route_information.acls_for_allow_http == [
        "req.hdr(host),field(1,:) -i example.com",
        "path_beg -i /path",
        "!path_beg -i /private",
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
        relation_ids_with_invalid_data=set(),
    )

    assert len(data.relation_ids_with_invalid_data) == 0


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
        relation_ids_with_invalid_data=set(),
    )

    assert data.relation_ids_with_invalid_data == {relation_id}


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
        relation_ids_with_invalid_data=set(),
    )

    assert data.relation_ids_with_invalid_data == {1, 2, 3, 4, 5}


def test_requirer_application_data_default_backend_default_is_false():
    """
    arrange: Create a RequirerApplicationData model without specifying default_backend.
    act: Check the default_backend value.
    assert: default_backend defaults to False.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
    )

    assert data.default_backend is False


@pytest.mark.parametrize("protocol", ["http", "https"])
def test_default_backend_with_external_grpc_port_is_invalid(protocol):
    """
    arrange: Set both default_backend and external_grpc_port in application data.
    act: Validate the application data.
    assert: Validation fails regardless of the backend protocol.
    """
    with pytest.raises(
        ValidationError, match="default_backend cannot be True when external_grpc_port is set"
    ):
        RequirerApplicationData(
            service="grpc-service",
            ports=[8080],
            protocol=protocol,
            external_grpc_port=9000,
            default_backend=True,
        )


@pytest.mark.parametrize(
    ("default_backend", "external_grpc_port"), [(False, None), (True, None), (False, 9000)]
)
def test_default_backend_and_external_grpc_port_valid_combinations(
    default_backend, external_grpc_port
):
    """
    arrange: Configure at most one of default_backend and external_grpc_port.
    act: Validate the application data.
    assert: Each supported combination is accepted.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        protocol="https",
        default_backend=default_backend,
        external_grpc_port=external_grpc_port,
    )

    assert data.default_backend is default_backend
    assert data.external_grpc_port == external_grpc_port


def test_single_default_backend_is_valid(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HaproxyRouteRequirersData with a single default backend.
    act: Instantiate HaproxyRouteRequirersData.
    assert: relation_ids_with_invalid_data is empty.
    """
    requirer_data = haproxy_route_relation_data(
        "default-service",
        relation_id=1,
        default_backend=True,
    )

    data = HaproxyRouteRequirersData(
        requirers_data=[requirer_data],
        relation_ids_with_invalid_data=set(),
    )

    assert data.relation_ids_with_invalid_data == set()


def test_multiple_default_backends_are_all_invalid(
    haproxy_route_relation_data: typing.Callable[..., HaproxyRouteRequirerData],
) -> None:
    """
    arrange: Create HaproxyRouteRequirersData with multiple default backends.
    act: Instantiate HaproxyRouteRequirersData.
    assert: all backends requesting to be the default backend are marked invalid.
    """
    requirer_data_1 = haproxy_route_relation_data(
        "default-service-1",
        relation_id=1,
        default_backend=True,
    )
    requirer_data_2 = haproxy_route_relation_data(
        "default-service-2",
        relation_id=2,
        default_backend=True,
    )
    requirer_data_3 = haproxy_route_relation_data(
        "regular-service",
        relation_id=3,
    )

    data = HaproxyRouteRequirersData(
        requirers_data=[requirer_data_1, requirer_data_2, requirer_data_3],
        relation_ids_with_invalid_data=set(),
    )

    assert data.relation_ids_with_invalid_data == {1, 2}


@pytest.fixture(name="mock_relation_data")
def mock_relation_data_fixture():
    """Create mock relation data."""
    return {
        "service": "test-service",
        "ports": [8080],
        "protocol": "http",
        "hosts": ["10.0.0.1", "10.0.0.2"],
        "paths": ["/api"],
        "hostname": "api.haproxy.internal",
        "load_balancing": {"algorithm": "leastconn"},
        "check": {"interval": 60, "rise": 2, "fall": 3, "path": "/health"},
        "http_server_close": True,
    }


@pytest.fixture(name="mock_unit_data")
def mock_unit_data_fixture():
    """Create mock unit data."""
    return {"address": MOCK_ADDRESS}


@pytest.fixture(name="mock_provider_app_data")
def mock_provider_app_data_fixture():
    """Create mock provider application data."""
    return HaproxyRouteProviderAppData(endpoints=["https://backend.haproxy.internal/path"]).dump()


def _build_requirer(app_data: dict[str, str]) -> HaproxyRouteRequirer:
    """Build a haproxy-route requirer backed by a mocked relation."""
    charm = MagicMock()
    relation = MagicMock()
    relation.app = MagicMock()
    relation.data = {relation.app: app_data}
    charm.model.get_relation.return_value = relation
    charm.framework.model.get_relation.return_value = relation
    return HaproxyRouteRequirer(charm=charm, relation_name=MOCK_RELATION_NAME)


def test_requirer_application_data_validation():
    """
    arrange: Create a RequirerApplicationData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        hosts=["10.0.0.1"],
        paths=["/api"],
        hostname="api.haproxy.internal",
        check=ServerHealthCheck(path="/health"),
        load_balancing={"algorithm": LoadBalancingAlgorithm.LEASTCONN},
    )

    assert data.service == "test-service"
    assert data.ports == [8080]
    assert data.hosts == [IPv4Address("10.0.0.1")]
    assert data.paths == ["/api"]
    assert data.hostname == "api.haproxy.internal"
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


def test_requirer_application_data_invalid_hosts():
    """
    arrange: Create a RequirerApplicationData model with hosts having invalid ip addresses.
    act: Validate the model.
    assert: Validation raises an error.
    """
    with pytest.raises(ValidationError):
        RequirerApplicationData(
            service="test-service",
            ports=[8080],
            hosts=["invalid"],
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
    assert: relation_ids_with_invalid_data contains the relations with duplicate services.
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

    data = HaproxyRouteRequirersData(
        requirers_data=[requirer_data1, requirer_data2], relation_ids_with_invalid_data=set()
    )

    assert data.relation_ids_with_invalid_data == {1, 2}


def test_load_legacy_requirer_application_data(mock_relation_data):
    """Validate that databag can be loaded from older version of the library."""
    databag = {k: json.dumps(v) for k, v in mock_relation_data.items()}
    databag.pop("protocol")
    data = RequirerApplicationData.load(databag)

    assert data.service == "test-service"
    assert data.ports == [8080]
    assert data.protocol == "http"  # the default value
    assert data.hosts == [IPv4Address("10.0.0.1"), IPv4Address("10.0.0.2")]
    assert data.paths == ["/api"]
    assert data.hostname == "api.haproxy.internal"
    assert data.check.interval == 60
    assert data.check.rise == 2
    assert data.check.fall == 3
    assert data.check.path == "/health"
    assert data.http_server_close is True


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
    assert data.protocol == "http"
    assert data.hosts == [IPv4Address("10.0.0.1"), IPv4Address("10.0.0.2")]
    assert data.paths == ["/api"]
    assert data.hostname == "api.haproxy.internal"
    assert data.check.interval == 60
    assert data.check.rise == 2
    assert data.check.fall == 3
    assert data.check.path == "/health"
    assert data.http_server_close is True


def test_dump_requirer_application_data():
    """
    arrange: Create a RequirerApplicationData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        hosts=["10.0.0.1"],
        paths=["/api"],
        hostname="api.haproxy.internal",
        check=ServerHealthCheck(path="/health"),
    )

    databag: dict[str, typing.Any] = {}
    data.dump(databag)

    assert "service" in databag
    assert json.loads(databag["service"]) == "test-service"
    assert json.loads(databag["ports"]) == [8080]
    assert json.loads(databag["hosts"]) == ["10.0.0.1"]
    assert json.loads(databag["paths"]) == ["/api"]
    assert json.loads(databag["hostname"]) == "api.haproxy.internal"
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


@pytest.mark.parametrize("default_backend", [False, True])
def test_provider_default_backend_with_external_grpc_port(default_backend):
    """
    arrange: Provide a gRPC relation with a configurable default_backend flag.
    act: Fetch the relation data from the provider.
    assert: Only the relation requesting both options is marked invalid and excluded.
    """
    relation_id = 1
    relation = MagicMock()
    relation.id = relation_id
    relation.app = MagicMock()
    relation.app.name = "grpc-service"
    relation.units = []
    relation.data = {
        relation.app: {
            "service": '"grpc-service"',
            "ports": "[8080]",
            "protocol": '"https"',
            "external_grpc_port": "9000",
            "default_backend": json.dumps(default_backend),
        }
    }
    provider = HaproxyRouteProvider(MagicMock())

    data = provider.get_data([relation])

    assert data.relation_ids_with_invalid_data == ({relation_id} if default_backend else set())
    assert [requirer.relation_id for requirer in data.requirers_data] == (
        [] if default_backend else [relation_id]
    )


def test_haproxy_route_provider_initialization():
    """
    arrange: Create a provider with a mock charm.
    act: Initialize the provider.
    assert: HaproxyRouteProvider is initialized correctly.
    """
    provider = HaproxyRouteProvider(MagicMock())

    # pylint: disable=protected-access
    assert provider._relation_name == MOCK_RELATION_NAME


def test_provide_haproxy_route_requirements(mock_relation_data):
    """Test that providing haproxy route requirements updates application data correctly."""
    requirer_charm = MagicMock()
    requirer_charm.unit.is_leader.return_value = True

    relation_mock = MagicMock()
    relation_data_mock = MagicMock()
    relation_mock.data.__getitem__.return_value = relation_data_mock

    requirer = HaproxyRouteRequirer(charm=requirer_charm, relation_name=MOCK_RELATION_NAME)
    requirer.relation = relation_mock

    # Update the requirements
    requirer.provide_haproxy_route_requirements(
        service=mock_relation_data["service"],
        ports=mock_relation_data["ports"],
        paths=mock_relation_data["paths"],
        hostname=mock_relation_data["hostname"],
        unit_address="10.0.1.0",
    )

    assert relation_data_mock.update.call_count == 2


def test_update_relation_data_non_leader(mock_relation_data):
    """Test that unit data is updated but app data is not when not the leader."""
    requirer_charm = MagicMock()
    requirer_charm.unit.is_leader.return_value = False

    relation_mock = MagicMock()
    relation_data_mock = MagicMock()
    relation_mock.data.__getitem__.return_value = relation_data_mock

    requirer = HaproxyRouteRequirer(charm=requirer_charm, relation_name=MOCK_RELATION_NAME)
    requirer.relation = relation_mock

    # Update the requirements
    requirer.provide_haproxy_route_requirements(
        service=mock_relation_data["service"],
        ports=mock_relation_data["ports"],
        paths=mock_relation_data["paths"],
        hostname=mock_relation_data["hostname"],
        unit_address="10.0.1.0",
    )

    relation_data_mock.update.assert_called_once()


def test_get_proxied_endpoints(mock_provider_app_data):
    """Test that get_proxied_endpoints returns the endpoints correctly."""
    requirer = _build_requirer(mock_provider_app_data)

    endpoints = requirer.get_proxied_endpoints()

    assert len(endpoints) == 1
    assert str(endpoints[0]) == json.loads(mock_provider_app_data["endpoints"])[0]


def test_get_proxied_endpoints_empty_data():
    """Test that get_proxied_endpoints returns empty list when no data."""
    requirer = _build_requirer({})

    assert requirer.get_proxied_endpoints() == []


def test_get_proxied_endpoints_invalid_data():
    """Test that get_proxied_endpoints handles invalid data gracefully."""
    requirer = _build_requirer({"endpoints": json.dumps(["invalid"])})

    assert requirer.get_proxied_endpoints() == []


def test_prepare_unit_data_no_address():
    """Test that DataValidationError is raised when no address is available."""
    requirer = _build_requirer({})

    # Reset the unit address and mock a binding with no address
    requirer.charm.model.get_binding.return_value = None

    with pytest.raises(DataValidationError):
        # We want to specifically test this method.
        requirer._prepare_unit_data()  # pylint: disable=protected-access


def test_requirer_application_data_incomplete_health_check():
    """
    arrange: Create a RequirerApplicationData model with incomplete health check configuration.
    act: Validate the model.
    assert: DataValidationError is raised.
    """
    with pytest.raises(ValidationError):
        RequirerApplicationData(
            service="test-service",
            ports=[8080],
            check=ServerHealthCheck(interval=60),
        )


def test_requirer_application_data_mismatch_load_balancing_configuration():
    """
    arrange: Create a RequirerApplicationData model with mismatch load balancing configuration.
    act: Validate the model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        RequirerApplicationData(
            service="test-service",
            ports=[8080],
            load_balancing=LoadBalancingConfiguration(
                algorithm=LoadBalancingAlgorithm.LEASTCONN, cookie="TEST", consistent_hashing=True
            ),
        )


def test_requirer_application_data_load_balancing_consistent_hashing_with_incorrect_algorithm():
    """
    arrange: Create a RequirerApplicationData model with consistent_hashing enabled
        and an incorrect algorithm.
    act: Validate the model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        RequirerApplicationData(
            service="test-service",
            ports=[8080],
            load_balancing=LoadBalancingConfiguration(
                algorithm=LoadBalancingAlgorithm.LEASTCONN, consistent_hashing=True
            ),
        )


# pylint: disable=no-member
def test_requirer_application_data_with_load_balancing_configuration():
    """
    arrange: Create a RequirerApplicationData model with mismatch load balancing configuration.
    act: Validate the model.
    assert: DataValidationError is raised.
    """
    application_data = RequirerApplicationData(
        service="test-service",
        ports=[8080],
        load_balancing=LoadBalancingConfiguration(
            algorithm=LoadBalancingAlgorithm.SRCIP, consistent_hashing=True
        ),
    )
    assert application_data.load_balancing.algorithm == LoadBalancingAlgorithm.SRCIP
    assert application_data.load_balancing.consistent_hashing is True
