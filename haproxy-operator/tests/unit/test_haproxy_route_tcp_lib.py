# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route-tcp interface library."""

import dataclasses
import json
import logging
from ipaddress import ip_address
from typing import Any
from unittest.mock import MagicMock

import pytest
from charms.haproxy.v2.haproxy_route_tcp import (
    HaproxyRouteTcpProvider,
    HaproxyRouteTcpProviderAppData,
    HaproxyRouteTcpRequirer,
    HaproxyRouteTcpRequirerData,
    LoadBalancingAlgorithm,
    PortMapping,
    PortRange,
    TCPHealthCheckType,
    TCPLoadBalancingConfiguration,
    TCPRateLimitPolicy,
    TcpRequirerApplicationData,
    TcpRequirerUnitData,
    TCPServerHealthCheck,
)
from pydantic import ValidationError

from .conftest import model_to_relation_data

logger = logging.getLogger()
MOCK_RELATION_NAME = "haproxy-route-tcp"
MOCK_ADDRESS = ip_address("10.0.0.1")
ANOTHER_MOCK_ADDRESS = ip_address("10.0.0.2")


def _encode_relation_data(data: Any, encoder) -> dict[str, str]:
    """Encode a dataclass the same way ops Relation.save does."""
    return {field: encoder(value) for field, value in dataclasses.asdict(data).items()}


def _decode_relation_data(databag: dict[str, str]) -> dict[str, Any]:
    """Decode a relation databag the same way ops Relation.load does."""
    return {key: json.loads(value) for key, value in databag.items()}


@pytest.fixture(name="mock_relation_data")
def mock_relation_data_fixture():
    """Create mock relation data."""
    return {
        "port": 8080,
        "backend_port": 9090,
        "hosts": [str(MOCK_ADDRESS), str(ANOTHER_MOCK_ADDRESS)],
        "sni": "api.haproxy.internal",
        "load_balancing": {"algorithm": "leastconn"},
        "check": {"interval": 60, "rise": 2, "fall": 3, "check_type": "generic"},
        "enforce_tls": True,
        "tls_terminate": True,
    }


@pytest.fixture(name="mock_unit_data")
def mock_unit_data_fixture():
    """Create mock unit data."""
    return {"address": str(MOCK_ADDRESS)}


@pytest.fixture(name="mock_provider_app_data")
def mock_provider_app_data_fixture():
    """Create mock provider app data."""
    return model_to_relation_data(
        HaproxyRouteTcpProviderAppData(endpoints=["backend.haproxy.internal:8080"])
    )


# pylint: disable=no-member
def test_requirer_application_data_validation():
    """
    arrange: Create a TcpRequirerApplicationData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = TcpRequirerApplicationData(
        port=8080,
        backend_port=9090,
        hosts=[MOCK_ADDRESS],
        sni="api.haproxy.internal",
        check=TCPServerHealthCheck(
            interval=60, rise=2, fall=3, check_type=TCPHealthCheckType.GENERIC
        ),
        load_balancing=TCPLoadBalancingConfiguration(algorithm=LoadBalancingAlgorithm.LEASTCONN),
        enforce_tls=True,
        tls_terminate=True,
    )

    assert data.port == 8080
    assert data.backend_port == 9090
    assert data.hosts == [MOCK_ADDRESS]
    assert data.sni == "api.haproxy.internal"
    assert data.check
    assert data.check.interval == 60
    assert data.check.rise == 2
    assert data.check.fall == 3
    assert data.check.check_type == TCPHealthCheckType.GENERIC
    assert data.load_balancing
    assert data.load_balancing.algorithm == LoadBalancingAlgorithm.LEASTCONN
    assert data.enforce_tls is True
    assert data.tls_terminate is True


def test_requirer_application_data_invalid_hosts():
    """
    arrange: Create a TcpRequirerApplicationData model with hosts having invalid ip addresses.
    act: Validate the model.
    assert: Validation raises an error.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(
            port=8080,
            # We want to force an invalid address here
            hosts=["invalid"],  # type: ignore
        )


def test_requirer_application_data_minimal_valid():
    """
    arrange: Create a TcpRequirerApplicationData model with minimal valid data.
    act: Validate the model.
    assert: Model validation passes with defaults.
    """
    data = TcpRequirerApplicationData(port=8080)

    assert data.port == 8080
    assert data.backend_port == 8080
    assert not data.hosts
    assert data.sni is None
    assert data.enforce_tls is True
    assert data.tls_terminate is True


def test_tcp_server_health_check_validation():
    """
    arrange: Create a TCPServerHealthCheck model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    check = TCPServerHealthCheck(
        interval=30,
        rise=3,
        fall=2,
        check_type=TCPHealthCheckType.GENERIC,
        send="PING",
        expect="PONG",
    )

    assert check.interval == 30
    assert check.rise == 3
    assert check.fall == 2
    assert check.check_type == TCPHealthCheckType.GENERIC
    assert check.send == "PING"
    assert check.expect == "PONG"


def test_tcp_load_balancing_configuration_validation():
    """
    arrange: Create a TCPLoadBalancingConfiguration model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    config = TCPLoadBalancingConfiguration(
        algorithm=LoadBalancingAlgorithm.SRCIP, consistent_hashing=True
    )

    assert config.algorithm == LoadBalancingAlgorithm.SRCIP
    assert config.consistent_hashing is True


def test_tcp_load_balancing_configuration_invalid_consistent_hashing():
    """
    arrange: Create a TCPLoadBalancingConfiguration with consistent_hashing and invalid algorithm.
    act: Validate the model.
    assert: Validation raises an error.
    """
    with pytest.raises(ValidationError):
        TCPLoadBalancingConfiguration(
            algorithm=LoadBalancingAlgorithm.LEASTCONN, consistent_hashing=True
        )


def test_requirer_unit_data_validation():
    """
    arrange: Create a TcpRequirerUnitData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = TcpRequirerUnitData(address=MOCK_ADDRESS)
    assert str(data.address) == str(MOCK_ADDRESS)


def test_tcp_requirers_data_duplicate_ports_are_mergeable():
    """
    arrange: Create HaproxyRouteTcpRequirersData with duplicate port numbers.
    act: Check conflict detection.
    assert: Same ports are not conflicting (they are mergeable into one frontend).
    """
    app_data1 = TcpRequirerApplicationData(port=8080)
    app_data2 = TcpRequirerApplicationData(port=8080)  # Same port

    tcp_requirer_data1 = HaproxyRouteTcpRequirerData(
        relation_id=1,
        application_data=app_data1,
        application="",
        units_data=[TcpRequirerUnitData(address=MOCK_ADDRESS)],
    )

    tcp_requirer_data2 = HaproxyRouteTcpRequirerData(
        relation_id=2,
        application_data=app_data2,
        application="",
        units_data=[TcpRequirerUnitData(address=ANOTHER_MOCK_ADDRESS)],
    )

    # Same port ranges are not conflicts — they are mergeable into one frontend
    conflicting = HaproxyRouteTcpProvider._get_invalid_port_range_relations(
        [tcp_requirer_data1, tcp_requirer_data2]
    )
    assert len(conflicting) == 0


def test_validate_requirer_application_data(mock_relation_data):
    """
    arrange: Create a dict with valid TCP application data.
    act: Validate the data with TcpRequirerApplicationData.
    assert: Data is loaded correctly.
    """
    data = TcpRequirerApplicationData(**mock_relation_data)

    assert data.port == 8080
    assert data.backend_port == 9090
    assert data.hosts == [ip_address("10.0.0.1"), ip_address("10.0.0.2")]
    assert data.sni == "api.haproxy.internal"
    assert data.check
    assert data.check.interval == 60
    assert data.check.rise == 2
    assert data.check.fall == 3
    assert data.check.check_type == TCPHealthCheckType.GENERIC
    assert data.enforce_tls is True
    assert data.tls_terminate is True


def test_dump_requirer_application_data_sni_with_tls_disabled():
    """
    arrange: Create a TcpRequirerApplicationData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(
            port=8080,
            sni="api.haproxy.internal",
            enforce_tls=False,
        )


def test_dump_requirer_application_data():
    """
    arrange: Create a TcpRequirerApplicationData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    data = TcpRequirerApplicationData(
        port=8080,
        backend_port=9090,
        hosts=[MOCK_ADDRESS],
        check=TCPServerHealthCheck(
            interval=60, rise=2, fall=3, check_type=TCPHealthCheckType.GENERIC
        ),
        enforce_tls=False,
        tls_terminate=False,
    )

    databag = model_to_relation_data(data)

    assert "port" in databag
    assert json.loads(databag["port"]) == 8080
    assert json.loads(databag["backend_port"]) == 9090
    assert json.loads(databag["hosts"]) == [str(ip_address("10.0.0.1"))]
    assert json.loads(databag["check"])["check_type"] == "generic"
    assert json.loads(databag["enforce_tls"]) is False
    assert json.loads(databag["tls_terminate"]) is False


def test_validate_requirer_unit_data(mock_unit_data):
    """
    arrange: Create a dict with valid unit data.
    act: Validate the data with TcpRequirerUnitData.
    assert: Data is loaded correctly.
    """
    data = TcpRequirerUnitData(**mock_unit_data)

    assert str(data.address) == str(MOCK_ADDRESS)


def test_dump_requirer_unit_data():
    """
    arrange: Create a TcpRequirerUnitData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    data = TcpRequirerUnitData(address=MOCK_ADDRESS)

    databag = model_to_relation_data(data)

    assert "address" in databag
    assert json.loads(databag["address"]) == str(MOCK_ADDRESS)


def test_get_proxied_endpoints_empty_data():
    """Test that HaproxyRouteTcpProviderAppData handles empty endpoints."""
    provider_data = HaproxyRouteTcpProviderAppData(endpoints=[])

    assert provider_data.endpoints == []


def test_get_proxied_endpoints_accepts_plain_strings():
    """Test that HaproxyRouteTcpProviderAppData accepts plain string endpoints."""
    data = HaproxyRouteTcpProviderAppData(endpoints=["10.0.0.1:8080", "api.example.com:443"])
    assert data.endpoints == ["10.0.0.1:8080", "api.example.com:443"]


def test_tcp_health_check_types():
    """
    arrange: Create TCPServerHealthCheck models with different health check types.
    act: Validate the models with different types.
    assert: All health check types are valid.
    """
    # Test generic health check
    generic_check = TCPServerHealthCheck(
        interval=30, rise=2, fall=3, check_type=TCPHealthCheckType.GENERIC
    )
    assert generic_check.check_type == TCPHealthCheckType.GENERIC

    # Test MySQL health check
    mysql_check = TCPServerHealthCheck(
        interval=30, rise=2, fall=3, check_type=TCPHealthCheckType.MYSQL, db_user="test_user"
    )
    assert mysql_check.check_type == TCPHealthCheckType.MYSQL
    assert mysql_check.db_user == "test_user"

    # Test PostgreSQL health check
    postgres_check = TCPServerHealthCheck(
        interval=30, rise=2, fall=3, check_type=TCPHealthCheckType.POSTGRES, db_user="test_user"
    )
    assert postgres_check.check_type == TCPHealthCheckType.POSTGRES
    assert postgres_check.db_user == "test_user"

    # Test Redis health check
    redis_check = TCPServerHealthCheck(
        interval=30,
        rise=2,
        fall=3,
        check_type=TCPHealthCheckType.REDIS,
    )
    assert redis_check.check_type == TCPHealthCheckType.REDIS

    # Test SMTP health check
    smtp_check = TCPServerHealthCheck(
        interval=30,
        rise=2,
        fall=3,
        check_type=TCPHealthCheckType.SMTP,
    )
    assert smtp_check.check_type == TCPHealthCheckType.SMTP


def test_requirer_application_data_with_ip_deny_list():
    """
    arrange: Create a TcpRequirerApplicationData model with IP deny list.
    act: Validate the model.
    assert: Model validation passes with IP deny list.
    """
    data = TcpRequirerApplicationData(
        port=8080, ip_deny_list=[ip_address("192.168.1.100"), ip_address("10.0.0.50")]
    )

    assert data.port == 8080
    assert len(data.ip_deny_list) == 2
    assert ip_address("192.168.1.100") in data.ip_deny_list
    assert ip_address("10.0.0.50") in data.ip_deny_list


def test_requirer_application_data_backend_port_defaults():
    """
    arrange: Create a TcpRequirerApplicationData model without backend_port.
    act: Validate the model.
    assert: backend_port defaults to None.
    """
    data = TcpRequirerApplicationData(port=8080)

    assert data.port == 8080
    assert data.backend_port == 8080


def test_requirer_application_data_tls_settings():
    """
    arrange: Create a TcpRequirerApplicationData model with different TLS settings.
    act: Validate the model.
    assert: TLS settings are correctly set.
    """
    # Test with enforce_tls=False, tls_terminate=False
    data1 = TcpRequirerApplicationData(port=8080, enforce_tls=False, tls_terminate=False)
    assert data1.enforce_tls is False
    assert data1.tls_terminate is False

    # Test with enforce_tls=True, tls_terminate=False
    data2 = TcpRequirerApplicationData(port=8080, enforce_tls=True, tls_terminate=False)
    assert data2.enforce_tls is True
    assert data2.tls_terminate is False


def test_tcp_load_balancing_roundrobin():
    """
    arrange: Create a TCPLoadBalancingConfiguration with roundrobin algorithm.
    act: Validate the model.
    assert: Model validation passes.
    """
    config = TCPLoadBalancingConfiguration(
        algorithm=LoadBalancingAlgorithm.ROUNDROBIN, consistent_hashing=False
    )

    assert config.algorithm == LoadBalancingAlgorithm.ROUNDROBIN
    assert config.consistent_hashing is False


def test_requirer_application_data_complete_configuration(mock_relation_data):
    """
    arrange: Create a TcpRequirerApplicationData model with complete configuration.
    act: Validate the model.
    assert: All fields are correctly set.
    """
    data = TcpRequirerApplicationData(
        port=mock_relation_data["port"],
        backend_port=mock_relation_data["backend_port"],
        hosts=mock_relation_data["hosts"],
        sni=mock_relation_data["sni"],
        check=TCPServerHealthCheck(
            interval=mock_relation_data["check"]["interval"],
            rise=mock_relation_data["check"]["rise"],
            fall=mock_relation_data["check"]["fall"],
            check_type=mock_relation_data["check"]["check_type"],
        ),
        load_balancing=TCPLoadBalancingConfiguration(algorithm=LoadBalancingAlgorithm.LEASTCONN),
        enforce_tls=mock_relation_data["enforce_tls"],
        tls_terminate=mock_relation_data["tls_terminate"],
        ip_deny_list=[ip_address("192.168.1.1")],
        server_maxconn=100,
    )

    assert data.port == 8080
    assert data.backend_port == 9090
    assert data.sni == "api.haproxy.internal"
    assert data.enforce_tls is True
    assert data.tls_terminate is True
    assert len(data.ip_deny_list) == 1
    assert data.server_maxconn == 100


@pytest.mark.parametrize(
    "invalid_sni",
    [
        "*.com",  # Wildcard at TLD level
        "*invalid.com",  # Asterisk not at start
        "test.*.com",  # Wildcard in the middle
    ],
)
def test_requirer_application_data_with_invalid_wildcard_sni(invalid_sni):
    """
    arrange: Create application data with invalid wildcard SNI.
    act: Attempt to create a TcpRequirerApplicationData model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(
            port=8080,
            sni=invalid_sni,
            enforce_tls=True,
        )


def test_requirer_application_data_proxy_protocol_defaults_to_false():
    """
    arrange: Create a TcpRequirerApplicationData model without proxy_protocol.
    act: Validate the model.
    assert: proxy_protocol defaults to False.
    """
    data = TcpRequirerApplicationData(port=8080)

    assert data.proxy_protocol is False


def test_requirer_application_data_proxy_protocol_enabled():
    """
    arrange: Create a TcpRequirerApplicationData model with proxy_protocol=True.
    act: Validate the model.
    assert: proxy_protocol is True.
    """
    data = TcpRequirerApplicationData(port=8080, proxy_protocol=True)

    assert data.proxy_protocol is True


def test_requirer_application_data_neither_port_nor_mapping():
    """
    arrange: Create a TcpRequirerApplicationData model without port or port_mapping.
    act: Validate the model.
    assert: Validation fails.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData()  # pyright: ignore[reportCallIssue]


# ---------------------------------------------------------------------------
# Helpers shared by the port-range / conflict-detection tests
# ---------------------------------------------------------------------------


def _make_requirer(
    relation_id: int, port: int, port_end: int | None = None
) -> HaproxyRouteTcpRequirerData:
    """Build a minimal HaproxyRouteTcpRequirerData for a given port (range)."""
    if port_end is None:
        app_data = TcpRequirerApplicationData(port=port)
    else:
        app_data = TcpRequirerApplicationData(port_mapping=f"{port}-{port_end}:{port}-{port_end}")
    return HaproxyRouteTcpRequirerData(
        relation_id=relation_id,
        application="test-app",
        application_data=app_data,
        units_data=[],
    )


# ---------------------------------------------------------------------------
# PortRange.__str__ tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start, end, expected",
    [
        pytest.param(8080, 8080, "8080", id="single_port_renders_as_plain_number"),
        pytest.param(8080, 8090, "8080-8090", id="range_renders_with_dash"),
    ],
)
def test_port_range_str(start, end, expected):
    """
    arrange: Create a PortRange with the given start and end.
    act: Convert to string.
    assert: Returns the expected string representation.
    """
    assert str(PortRange(start, end)) == expected


# ---------------------------------------------------------------------------
# PortRange equality tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, equal",
    [
        pytest.param(PortRange(8080, 8080), PortRange(8080, 8080), True, id="same_single_port"),
        pytest.param(PortRange(8080, 8090), PortRange(8080, 8090), True, id="same_range"),
        pytest.param(PortRange(8079, 8090), PortRange(8080, 8090), False, id="different_start"),
        pytest.param(PortRange(8080, 8089), PortRange(8080, 8090), False, id="different_end"),
    ],
)
def test_port_range_equality(a, b, equal):
    """
    arrange: Two PortRanges.
    act: Compare with == and !=.
    assert: Equality matches the expected result.
    """
    assert (a == b) == equal
    assert (a != b) == (not equal)


def test_port_range_not_equal_to_plain_tuple():
    """
    arrange: A PortRange and a plain tuple with the same values.
    act: Compare with !=.
    assert: They are not equal.
    """
    assert PortRange(8080, 8090) != (8080, 8090)
    assert PortRange(8080, 8090) != "8080-8090"


# ---------------------------------------------------------------------------
# PortRange.overlaps_with tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, expected",
    [
        pytest.param(PortRange(8080, 8080), PortRange(8080, 8080), True, id="same_single_port"),
        pytest.param(PortRange(8080, 8090), PortRange(8080, 8090), True, id="same_range"),
        pytest.param(
            PortRange(8080, 8080),
            PortRange(8081, 8081),
            False,
            id="adjacent_single_ports_do_not_overlap",
        ),
        pytest.param(
            PortRange(8080, 8080),
            PortRange(8090, 8090),
            False,
            id="far_apart_single_ports_do_not_overlap",
        ),
        pytest.param(
            PortRange(8080, 8090), PortRange(8085, 8085), True, id="single_port_inside_range"
        ),
        pytest.param(
            PortRange(8080, 8090),
            PortRange(8080, 8080),
            True,
            id="single_port_at_range_start",
        ),
        pytest.param(
            PortRange(8080, 8090), PortRange(8090, 8090), True, id="single_port_at_range_end"
        ),
        pytest.param(
            PortRange(8080, 8090),
            PortRange(8079, 8079),
            False,
            id="single_port_before_range",
        ),
        pytest.param(
            PortRange(8080, 8090),
            PortRange(8091, 8091),
            False,
            id="single_port_after_range",
        ),
        pytest.param(PortRange(8080, 8090), PortRange(8085, 8095), True, id="partial_overlap"),
        pytest.param(PortRange(8000, 9000), PortRange(8080, 8090), True, id="one_contains_other"),
        pytest.param(PortRange(8080, 8090), PortRange(8090, 8100), True, id="touch_at_boundary"),
        pytest.param(
            PortRange(8080, 8090),
            PortRange(8091, 8100),
            False,
            id="one_port_past_boundary_no_overlap",
        ),
    ],
)
def test_port_range_overlaps_with(a, b, expected):
    """
    arrange: Two PortRanges.
    act: Check overlaps_with.
    assert: Returns the expected boolean.
    """
    assert a.overlaps_with(b) == expected


def test_port_range_overlaps_with_is_symmetric():
    """
    arrange: Two partially overlapping PortRanges.
    act: Check overlaps_with in both directions.
    assert: Both directions return the same result.
    """
    a = PortRange(8080, 8090)
    b = PortRange(8085, 8095)
    assert a.overlaps_with(b) == b.overlaps_with(a)


# ---------------------------------------------------------------------------
# HaproxyRouteTcpProvider._get_invalid_port_range_relations tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "requirers, expected",
    [
        pytest.param([], set(), id="empty_list"),
        pytest.param(
            [_make_requirer(1, 8080)],
            set(),
            id="single_requirer",
        ),
        pytest.param(
            [_make_requirer(1, 8080), _make_requirer(2, 8080)],
            set(),
            id="two_same_single_port_not_conflicting",
        ),
        pytest.param(
            [_make_requirer(1, 8080, 8090), _make_requirer(2, 8080, 8090)],
            {1, 2},
            id="two_same_range_conflicting",
        ),
        pytest.param(
            [_make_requirer(i, 8080) for i in range(1, 6)],
            set(),
            id="many_same_single_port_all_valid",
        ),
        pytest.param(
            [_make_requirer(1, 8080), _make_requirer(2, 8090)],
            set(),
            id="two_non_overlapping_single_ports",
        ),
        pytest.param(
            [_make_requirer(1, 8080, 8090), _make_requirer(2, 8091, 8100)],
            set(),
            id="two_non_overlapping_ranges",
        ),
        pytest.param(
            [_make_requirer(1, 8080), _make_requirer(2, 8090, 8100), _make_requirer(3, 8110)],
            set(),
            id="three_all_non_overlapping",
        ),
        pytest.param(
            [
                _make_requirer(1, 8000, 8010),
                _make_requirer(2, 8000, 8010),
                _make_requirer(3, 8100, 8110),
                _make_requirer(4, 8100, 8110),
            ],
            {1, 2, 3, 4},
            id="two_groups_same_range_each_conflict",
        ),
        pytest.param(
            [_make_requirer(1, 8080, 8090), _make_requirer(2, 8085)],
            set(),
            id="single_port_inside_range_is_mergeable",
        ),
        pytest.param(
            [_make_requirer(1, 8080, 8090), _make_requirer(2, 8085, 8095)],
            {1, 2},
            id="two_partially_overlapping_ranges",
        ),
        pytest.param(
            [_make_requirer(1, 8000, 9000), _make_requirer(2, 8080, 8090)],
            {1, 2},
            id="umbrella_range_contains_smaller",
        ),
        pytest.param(
            [_make_requirer(1, 8080, 8090), _make_requirer(2, 8090, 8100)],
            {1, 2},
            id="boundary_touch_is_conflict",
        ),
        pytest.param(
            [_make_requirer(1, 8080, 8090), _make_requirer(2, 8091, 8100)],
            set(),
            id="one_port_past_boundary_no_conflict",
        ),
        pytest.param(
            [
                _make_requirer(1, 8080, 8090),
                _make_requirer(2, 8085, 8095),
                _make_requirer(3, 8110),
            ],
            {1, 2},
            id="first_two_ranges_conflict_single_clean",
        ),
        pytest.param(
            [_make_requirer(1, 8080), _make_requirer(2, 8090, 8100), _make_requirer(3, 8095)],
            set(),
            id="single_inside_range_no_conflict",
        ),
        pytest.param(
            [
                _make_requirer(1, 8080, 8090),
                _make_requirer(2, 8085, 8100),
                _make_requirer(3, 8098, 8110),
            ],
            {1, 2, 3},
            id="chain_overlap_all_three_flagged",
        ),
        pytest.param(
            [
                _make_requirer(1, 8080, 8090),
                _make_requirer(2, 8080, 8090),
                _make_requirer(3, 8085, 8100),
            ],
            {1, 2, 3},
            id="three_overlapping_ranges_all_flagged",
        ),
        pytest.param(
            [
                _make_requirer(1, 8080),
                _make_requirer(2, 8090, 8100),
                _make_requirer(3, 8095, 8105),
                _make_requirer(4, 8120),
            ],
            {2, 3},
            id="complex_mixed_single_and_ranges",
        ),
        pytest.param(
            [_make_requirer(1, 8095), _make_requirer(2, 8080, 8090)],
            set(),
            id="unsorted_non_conflicting_input",
        ),
        pytest.param(
            [_make_requirer(2, 8085, 8095), _make_requirer(1, 8080, 8090)],
            {1, 2},
            id="unsorted_conflicting_input",
        ),
    ],
)
def test_get_invalid_port_range_relations(requirers, expected):
    """
    arrange: A list of requirers with given port/range specs.
    act: Run conflict detection.
    assert: The set of conflicting relation IDs matches expected.
    """
    assert HaproxyRouteTcpProvider._get_invalid_port_range_relations(requirers) == expected


# ---------------------------------------------------------------------------
# PortMapping tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, frontend, backend, offset",
    [
        pytest.param(
            "8080:8080", PortRange(8080, 8080), PortRange(8080, 8080), 0, id="single_no_offset"
        ),
        pytest.param(
            "8080:9090",
            PortRange(8080, 8080),
            PortRange(9090, 9090),
            1010,
            id="single_positive_offset",
        ),
        pytest.param(
            "9090:8080",
            PortRange(9090, 9090),
            PortRange(8080, 8080),
            -1010,
            id="single_negative_offset",
        ),
        pytest.param(
            "8080-8090:9080-9090",
            PortRange(8080, 8090),
            PortRange(9080, 9090),
            1000,
            id="range_positive_offset",
        ),
        pytest.param(
            "9080-9090:8080-8090",
            PortRange(9080, 9090),
            PortRange(8080, 8090),
            -1000,
            id="range_negative_offset",
        ),
        pytest.param(
            "8080-8090:8080-8090",
            PortRange(8080, 8090),
            PortRange(8080, 8090),
            0,
            id="range_no_offset",
        ),
    ],
)
def test_port_mapping_from_string(value, frontend, backend, offset):
    """
    arrange: A valid port mapping string.
    act: Parse it with PortMapping.from_string.
    assert: The frontend/backend ranges and offset match expectations.
    """
    mapping = PortMapping.from_string(value)
    assert mapping.frontend == frontend
    assert mapping.backend == backend
    assert mapping.offset == offset


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("8080", id="missing_backend"),
        pytest.param("8080:9090:1010", id="too_many_parts"),
        pytest.param("8080-8090:9080-9095", id="different_lengths"),
        pytest.param("8080-:9090", id="malformed_range"),
        pytest.param("abc:9090", id="non_numeric"),
        pytest.param("0:9090", id="port_zero"),
        pytest.param("70000:9090", id="port_out_of_bounds"),
        pytest.param("8090-8080:9090-9100", id="start_greater_than_end"),
    ],
)
def test_port_mapping_from_string_invalid(value):
    """
    arrange: A malformed port mapping string.
    act: Parse it with PortMapping.from_string.
    assert: A ValueError is raised.
    """
    with pytest.raises(ValueError):
        PortMapping.from_string(value)


def test_port_mapping_str_roundtrip():
    """
    arrange: A PortMapping built from a string.
    act: Convert it back to a string.
    assert: The canonical string representation is returned.
    """
    assert str(PortMapping.from_string("8080-8090:9080-9090")) == "8080-8090:9080-9090"
    assert str(PortMapping.from_string("8080:9090")) == "8080:9090"


# ---------------------------------------------------------------------------
# TcpRequirerApplicationData port_mapping tests
# ---------------------------------------------------------------------------


def test_requirer_application_data_port_mapping_range():
    """
    arrange: Create application data with a port_mapping range.
    act: Validate the model and read the derived properties.
    assert: The frontend/backend ranges and offset are derived from the mapping.
    """
    data = TcpRequirerApplicationData(port_mapping="8080-8090:9080-9090")

    assert data.port is None
    assert data.backend_port is None
    assert data.is_port_range is True
    assert data.port_range == PortRange(8080, 8090)
    assert data.backend_port_range == PortRange(9080, 9090)
    assert data.effective_port_mapping.offset == 1000


def test_requirer_application_data_port_builds_mapping():
    """
    arrange: Create application data with port and backend_port set.
    act: Read the derived port mapping.
    assert: The mapping is built from port and backend_port.
    """
    data = TcpRequirerApplicationData(port=8080, backend_port=9090)

    assert data.is_port_range is False
    assert data.port_range == PortRange(8080, 8080)
    assert data.backend_port_range == PortRange(9090, 9090)
    assert data.effective_port_mapping.offset == 1010


def test_requirer_application_data_port_only_zero_offset():
    """
    arrange: Create application data with only port set.
    act: Read the derived port mapping.
    assert: backend_port defaults to port, giving a zero offset.
    """
    data = TcpRequirerApplicationData(port=8080)

    assert data.backend_port == 8080
    assert data.effective_port_mapping.offset == 0


def test_requirer_application_data_port_mapping_with_port_raises():
    """
    arrange: Create application data with both port_mapping and port.
    act: Validate the model.
    assert: Validation fails because they are mutually exclusive.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port=8080, port_mapping="8080:9090")


def test_requirer_application_data_port_mapping_with_backend_port_raises():
    """
    arrange: Create application data with both port_mapping and backend_port.
    act: Validate the model.
    assert: Validation fails because they are mutually exclusive.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(backend_port=9090, port_mapping="8080:9090")


def test_requirer_application_data_invalid_port_mapping_raises():
    """
    arrange: Create application data with a malformed port_mapping.
    act: Validate the model.
    assert: Validation fails.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port_mapping="8080-8090:9080-9095")


def test_requirer_saves_relation_data():
    """
    arrange: Create a requirer with a mocked relation and a configured unit address.
    act: Provide the requirer requirements.
    assert: Application and unit data are saved using the ops relation API.
    """
    charm = MagicMock()
    charm.unit.is_leader.return_value = True
    requirer = HaproxyRouteTcpRequirer(charm=charm, relation_name=MOCK_RELATION_NAME)
    relation = MagicMock()
    requirer.relation = relation

    requirer.provide_haproxy_route_tcp_requirements(port=4000, unit_address="10.0.0.1")

    assert relation.save.call_count == 2
    application_data, app_destination = relation.save.call_args_list[0].args
    unit_data, unit_destination = relation.save.call_args_list[1].args
    assert app_destination is charm.app
    assert unit_destination is charm.unit
    assert application_data.port == 4000
    assert application_data.backend_port == 4000
    assert str(unit_data.address) == "10.0.0.1"


def test_requirer_application_data_encoder_handles_non_json_serializable_defaults():
    """
    arrange: Create a requirer with valid but minimally configured application data.
    act: Encode the application data with the encoder passed to the relation.
    assert: Enum defaults that are not natively JSON serializable are encoded and loaded.
    """
    charm = MagicMock()
    charm.unit.is_leader.return_value = True
    requirer = HaproxyRouteTcpRequirer(charm=charm, relation_name=MOCK_RELATION_NAME)
    relation = MagicMock()
    requirer.relation = relation

    requirer.provide_haproxy_route_tcp_requirements(
        port=4000,
        unit_address="10.0.0.1",
        load_balancing_algorithm=LoadBalancingAlgorithm.LEASTCONN,
        rate_limit_connections_per_minute=60,
    )

    application_data, _ = relation.save.call_args_list[0].args
    encoder = relation.save.call_args_list[0].kwargs["encoder"]
    databag = _encode_relation_data(application_data, encoder)

    assert json.loads(databag["load_balancing"]) == {
        "algorithm": "leastconn",
        "consistent_hashing": False,
    }
    assert json.loads(databag["rate_limit"]) == {
        "connections_per_minute": 60,
        "policy": "reject",
    }

    loaded = TcpRequirerApplicationData(**_decode_relation_data(databag))

    assert loaded.load_balancing.algorithm == LoadBalancingAlgorithm.LEASTCONN  # pylint: disable=no-member
    assert loaded.rate_limit.policy == TCPRateLimitPolicy.REJECT  # pylint: disable=no-member


def test_requirer_application_data_round_trip_with_all_fields():
    """
    arrange: Create a requirer with checks, limits, timeouts and TLS configuration.
    act: Encode the requirer data with the ops relation encoder and load it back.
    assert: Every representative field is serialized and deserialized correctly.
    """
    charm = MagicMock()
    charm.unit.is_leader.return_value = True
    requirer = HaproxyRouteTcpRequirer(charm=charm, relation_name=MOCK_RELATION_NAME)
    relation = MagicMock()
    requirer.relation = relation

    requirer.provide_haproxy_route_tcp_requirements(
        port=4000,
        backend_port=5000,
        hosts=["10.0.0.1", "10.0.0.2"],
        sni="api.haproxy.internal",
        check_interval=15,
        check_rise=3,
        check_fall=2,
        check_type=TCPHealthCheckType.GENERIC,
        check_send="PING",
        check_expect="PONG",
        load_balancing_algorithm=LoadBalancingAlgorithm.SRCIP,
        load_balancing_consistent_hashing=True,
        rate_limit_connections_per_minute=120,
        rate_limit_policy=TCPRateLimitPolicy.SILENT,
        upload_limit=1024,
        download_limit=2048,
        retry_count=3,
        retry_redispatch=True,
        server_timeout=45,
        connect_timeout=15,
        queue_timeout=5,
        server_maxconn=250,
        ip_deny_list=["10.0.0.9"],
        enforce_tls=True,
        tls_terminate=True,
        proxy_protocol=True,
        unit_address="10.0.0.1",
    )

    application_data, _ = relation.save.call_args_list[0].args
    unit_data, _ = relation.save.call_args_list[1].args
    encoder = relation.save.call_args_list[0].kwargs["encoder"]
    databag = _encode_relation_data(application_data, encoder)
    unit_databag = _encode_relation_data(unit_data, encoder)

    assert json.loads(databag["hosts"]) == ["10.0.0.1", "10.0.0.2"]
    assert json.loads(databag["check"]) == {
        "interval": 15,
        "rise": 3,
        "fall": 2,
        "check_type": "generic",
        "send": "PING",
        "expect": "PONG",
        "db_user": None,
    }
    assert json.loads(databag["load_balancing"]) == {
        "algorithm": "source",
        "consistent_hashing": True,
    }
    assert json.loads(databag["rate_limit"]) == {
        "connections_per_minute": 120,
        "policy": "silent-drop",
    }
    assert json.loads(databag["bandwidth_limit"]) == {"upload": 1024, "download": 2048}
    assert json.loads(databag["retry"]) == {"count": 3, "redispatch": True}
    assert json.loads(databag["timeout"]) == {"server": 45, "connect": 15, "queue": 5}
    assert json.loads(databag["ip_deny_list"]) == ["10.0.0.9"]
    assert json.loads(unit_databag["address"]) == "10.0.0.1"

    loaded = TcpRequirerApplicationData(**_decode_relation_data(databag))
    loaded_unit = TcpRequirerUnitData(**_decode_relation_data(unit_databag))

    assert loaded.port == 4000
    assert loaded.backend_port == 5000
    assert [str(host) for host in loaded.hosts] == ["10.0.0.1", "10.0.0.2"]
    assert loaded.sni == "api.haproxy.internal"
    assert loaded.check == TCPServerHealthCheck(
        interval=15,
        rise=3,
        fall=2,
        check_type=TCPHealthCheckType.GENERIC,
        send="PING",
        expect="PONG",
    )
    assert loaded.load_balancing == TCPLoadBalancingConfiguration(
        algorithm=LoadBalancingAlgorithm.SRCIP, consistent_hashing=True
    )
    assert loaded.rate_limit.connections_per_minute == 120  # pylint: disable=no-member
    assert loaded.rate_limit.policy == TCPRateLimitPolicy.SILENT  # pylint: disable=no-member
    assert loaded.bandwidth_limit.upload == 1024  # pylint: disable=no-member
    assert loaded.bandwidth_limit.download == 2048  # pylint: disable=no-member
    assert loaded.retry.count == 3  # pylint: disable=no-member
    assert loaded.retry.redispatch is True  # pylint: disable=no-member
    assert loaded.timeout.server == 45  # pylint: disable=no-member
    assert loaded.timeout.connect == 15  # pylint: disable=no-member
    assert loaded.timeout.queue == 5  # pylint: disable=no-member
    assert loaded.server_maxconn == 250
    assert [str(address) for address in loaded.ip_deny_list] == ["10.0.0.9"]
    assert loaded.proxy_protocol is True
    assert str(loaded_unit.address) == "10.0.0.1"


def test_provider_loads_requirer_data():
    """
    arrange: Create a provider with a mocked relation exposing requirer data.
    act: Fetch the data with HaproxyRouteTcpProvider.get_data().
    assert: The loaded requirer application and unit data are returned.
    """
    charm = MagicMock()
    provider = HaproxyRouteTcpProvider(charm)
    relation = MagicMock()
    relation.id = 1
    relation.app.name = "tcp-requirer"
    relation.units = [MagicMock()]
    application_data = TcpRequirerApplicationData(port=4000)
    unit_data = TcpRequirerUnitData(address=MOCK_ADDRESS)

    def _load(cls, _):
        if cls is TcpRequirerApplicationData:
            return application_data
        return unit_data

    relation.load.side_effect = _load

    data = provider.get_data([relation])

    assert data.relation_ids_with_invalid_data == set()
    assert data.requirers_data[0].application_data == application_data
    assert data.requirers_data[0].units_data == [unit_data]


def test_provider_publishes_proxied_endpoints():
    """
    arrange: Create a provider with a mocked relation.
    act: Publish proxied endpoints and encode them with the ops relation encoder.
    assert: The endpoints are saved to the provider application databag.
    """
    charm = MagicMock()
    provider = HaproxyRouteTcpProvider(charm)
    relation = MagicMock()
    relation.load.side_effect = ValueError

    provider.publish_proxied_endpoints(["api.haproxy.internal:4000", "10.0.0.1:4000"], relation)

    saved_data, destination = relation.save.call_args.args
    encoder = relation.save.call_args.kwargs["encoder"]
    assert destination is charm.app

    databag = _encode_relation_data(saved_data, encoder)
    assert json.loads(databag["endpoints"]) == [
        "api.haproxy.internal:4000",
        "10.0.0.1:4000",
    ]

    loaded = HaproxyRouteTcpProviderAppData(**_decode_relation_data(databag))
    assert loaded.endpoints == ["api.haproxy.internal:4000", "10.0.0.1:4000"]
