# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route-tcp interface library."""

import json
import logging
from ipaddress import ip_address
from typing import Any, cast

import pytest
from charms.haproxy.v1.haproxy_route_tcp import (
    HaproxyRouteTcpProviderAppData,
    HaproxyRouteTcpRequirerData,
    HaproxyRouteTcpRequirersData,
    LoadBalancingAlgorithm,
    TCPHealthCheckType,
    TCPLoadBalancingConfiguration,
    TcpRequirerApplicationData,
    TcpRequirerUnitData,
    TCPServerHealthCheck,
)
from pydantic import AnyHttpUrl, ValidationError

logger = logging.getLogger()
MOCK_RELATION_NAME = "haproxy-route-tcp"
MOCK_ADDRESS = ip_address("10.0.0.1")
ANOTHER_MOCK_ADDRESS = ip_address("10.0.0.2")


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
    return HaproxyRouteTcpProviderAppData(
        endpoints=[cast(AnyHttpUrl, "https://backend.haproxy.internal:8080")]
    ).dump()


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


def test_provider_app_data_validation():
    """
    arrange: Create a HaproxyRouteTcpProviderAppData model with valid data.
    act: Validate the model.
    assert: Model validation passes.
    """
    data = HaproxyRouteTcpProviderAppData(endpoints=[cast(AnyHttpUrl, "https://example.com:8080")])
    # Note: pydantic automatically adds a trailing slash '/'
    # after validating the URL, this is intended behavior
    assert [str(endpoint) for endpoint in data.endpoints] == ["https://example.com:8080/"]


def test_tcp_requirers_data_duplicate_ports():
    """
    arrange: Create HaproxyRouteTcpRequirersData with duplicate port numbers.
    act: Validate the model.
    assert: Validation updates relation_ids_with_invalid_data.
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

    requirers_data = HaproxyRouteTcpRequirersData(
        requirers_data=[tcp_requirer_data1, tcp_requirer_data2],
        relation_ids_with_invalid_data=set(),
    )

    # The validator should detect duplicate ports and add relation IDs to invalid list
    assert len(requirers_data.relation_ids_with_invalid_data) == 2


def test_load_requirer_application_data(mock_relation_data):
    """
    arrange: Create a databag with valid TCP application data.
    act: Load the data with TcpRequirerApplicationData.load().
    assert: Data is loaded correctly.
    """
    databag = {k: json.dumps(v) for k, v in mock_relation_data.items()}
    data = cast(TcpRequirerApplicationData, TcpRequirerApplicationData.load(databag))

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

    databag = cast(dict[str, Any], data.dump())

    assert "port" in databag
    assert json.loads(databag["port"]) == 8080
    assert json.loads(databag["backend_port"]) == 9090
    assert json.loads(databag["hosts"]) == [str(ip_address("10.0.0.1"))]
    assert json.loads(databag["check"])["check_type"] == "generic"
    assert json.loads(databag["enforce_tls"]) is False
    assert json.loads(databag["tls_terminate"]) is False


def test_load_requirer_unit_data(mock_unit_data):
    """
    arrange: Create a databag with valid unit data.
    act: Load the data with TcpRequirerUnitData.load().
    assert: Data is loaded correctly.
    """
    databag = {k: json.dumps(v) for k, v in mock_unit_data.items()}
    data = cast(TcpRequirerUnitData, TcpRequirerUnitData.load(databag))

    assert str(data.address) == str(MOCK_ADDRESS)


def test_dump_requirer_unit_data():
    """
    arrange: Create a TcpRequirerUnitData model with valid data.
    act: Dump the model to a databag.
    assert: Databag contains correct data.
    """
    data = TcpRequirerUnitData(address=MOCK_ADDRESS)

    databag: dict[str, str] = {}
    data.dump(databag)

    assert "address" in databag
    assert json.loads(databag["address"]) == str(MOCK_ADDRESS)


def test_get_proxied_endpoints_with_valid_data(mock_provider_app_data):
    """Test that endpoints can be loaded from valid provider data."""
    provider_data = cast(
        HaproxyRouteTcpProviderAppData, HaproxyRouteTcpProviderAppData.load(mock_provider_app_data)
    )

    assert len(provider_data.endpoints) == 1
    assert str(provider_data.endpoints[0]) == "https://backend.haproxy.internal:8080/"


def test_get_proxied_endpoints_empty_data():
    """Test that HaproxyRouteTcpProviderAppData handles empty endpoints."""
    provider_data = HaproxyRouteTcpProviderAppData(endpoints=[])

    assert provider_data.endpoints == []


def test_get_proxied_endpoints_invalid_data():
    """Test that HaproxyRouteTcpProviderAppData validation fails with invalid URLs."""
    with pytest.raises(ValidationError):
        HaproxyRouteTcpProviderAppData(endpoints=[cast(AnyHttpUrl, "invalid")])


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


def test_requirer_application_data_wildcard_sni_without_tls_fails():
    """
    arrange: Create application data with wildcard SNI but TLS disabled.
    act: Attempt to create a TcpRequirerApplicationData model.
    assert: ValidationError is raised because SNI requires TLS.
    """
    with pytest.raises(ValidationError, match="can't set SNI and disable TLS"):
        TcpRequirerApplicationData(
            port=8080,
            sni="*.example.com",
            enforce_tls=False,
        )
