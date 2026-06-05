# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for port-range support in haproxy-route-tcp."""

from ipaddress import ip_address

import pytest
from charms.haproxy.v1.haproxy_route_tcp import (
    HaproxyRouteTcpRequirerData,
    HaproxyRouteTcpRequirersData,
    TcpRequirerApplicationData,
    TcpRequirerUnitData,
)
from pydantic import ValidationError

MOCK_ADDRESS = ip_address("10.0.0.1")
ANOTHER_MOCK_ADDRESS = ip_address("10.0.0.2")


# ---------------------------------------------------------------------------
# Library: TcpRequirerApplicationData port_range field
# ---------------------------------------------------------------------------


def test_port_range_valid():
    """
    arrange: Create TcpRequirerApplicationData with a valid port_range.
    act: Validate the model.
    assert: port_range is stored and port is None.
    """
    data = TcpRequirerApplicationData(port_range=(10500, 10600))

    assert data.port_range == (10500, 10600)
    assert data.port is None
    assert data.backend_port is None


def test_port_range_and_port_mutually_exclusive():
    """
    arrange: Create TcpRequirerApplicationData with both port and port_range set.
    act: Validate the model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port=8080, port_range=(10500, 10600))


def test_neither_port_nor_port_range():
    """
    arrange: Create TcpRequirerApplicationData without port or port_range.
    act: Validate the model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData()


def test_port_range_end_must_exceed_start():
    """
    arrange: Create TcpRequirerApplicationData with port_range where end <= start.
    act: Validate the model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port_range=(10600, 10500))

    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port_range=(10500, 10500))


def test_port_range_values_must_be_valid():
    """
    arrange: Create TcpRequirerApplicationData with out-of-range port_range values.
    act: Validate the model.
    assert: ValidationError is raised.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port_range=(0, 100))

    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port_range=(100, 65536))


def test_port_range_backend_port_must_match_start():
    """
    arrange: Create TcpRequirerApplicationData with port_range and a shifted backend_port.
    act: Validate the model.
    assert: ValidationError is raised for shifted backend_port.
    """
    with pytest.raises(ValidationError):
        TcpRequirerApplicationData(port_range=(10500, 10600), backend_port=9000)


def test_port_range_allows_backend_port_equal_to_start():
    """
    arrange: Create TcpRequirerApplicationData with port_range and backend_port == range start.
    act: Validate the model.
    assert: Validation passes (lenient: same port is fine).
    """
    data = TcpRequirerApplicationData(port_range=(10500, 10600), backend_port=10500)
    assert data.port_range == (10500, 10600)
    assert data.backend_port == 10500


def test_port_range_no_default_backend_port():
    """
    arrange: Create TcpRequirerApplicationData with port_range and no backend_port.
    act: Validate the model.
    assert: backend_port remains None (assign_default_backend_port skipped).
    """
    data = TcpRequirerApplicationData(port_range=(10500, 10600))
    assert data.backend_port is None


def test_port_range_serialization():
    """
    arrange: Create TcpRequirerApplicationData with port_range.
    act: Dump to databag and reload.
    assert: port_range round-trips correctly.
    """
    original = TcpRequirerApplicationData(port_range=(10500, 10600))
    databag = original.dump()
    assert databag is not None

    loaded = TcpRequirerApplicationData.load(databag)
    assert loaded.port_range == (10500, 10600)
    assert loaded.port is None


# ---------------------------------------------------------------------------
# Library: check_ports_unique with ranges
# ---------------------------------------------------------------------------


def _make_requirer(relation_id: int, **app_data_kwargs) -> HaproxyRouteTcpRequirerData:
    """Helper to create a HaproxyRouteTcpRequirerData."""
    return HaproxyRouteTcpRequirerData(
        relation_id=relation_id,
        application="app",
        application_data=TcpRequirerApplicationData(**app_data_kwargs),
        units_data=[TcpRequirerUnitData(address=MOCK_ADDRESS)],
    )


def test_check_ports_unique_overlapping_ranges():
    """
    arrange: Two requirers with overlapping port ranges.
    act: Build HaproxyRouteTcpRequirersData.
    assert: Both are marked invalid.
    """
    r1 = _make_requirer(1, port_range=(10500, 10600))
    r2 = _make_requirer(2, port_range=(10580, 10700))

    data = HaproxyRouteTcpRequirersData(
        requirers_data=[r1, r2], relation_ids_with_invalid_data=set()
    )
    assert 1 in data.relation_ids_with_invalid_data
    assert 2 in data.relation_ids_with_invalid_data


def test_check_ports_unique_non_overlapping_ranges():
    """
    arrange: Two requirers with non-overlapping port ranges.
    act: Build HaproxyRouteTcpRequirersData.
    assert: Neither is marked invalid.
    """
    r1 = _make_requirer(1, port_range=(10500, 10600))
    r2 = _make_requirer(2, port_range=(10601, 10700))

    data = HaproxyRouteTcpRequirersData(
        requirers_data=[r1, r2], relation_ids_with_invalid_data=set()
    )
    assert not data.relation_ids_with_invalid_data


def test_check_ports_unique_range_overlaps_single_port():
    """
    arrange: A range requirer and a single-port requirer whose port falls in the range.
    act: Build HaproxyRouteTcpRequirersData.
    assert: Both are marked invalid.
    """
    r1 = _make_requirer(1, port_range=(10500, 10600))
    r2 = _make_requirer(2, port=10550)

    data = HaproxyRouteTcpRequirersData(
        requirers_data=[r1, r2], relation_ids_with_invalid_data=set()
    )
    assert 1 in data.relation_ids_with_invalid_data
    assert 2 in data.relation_ids_with_invalid_data


def test_check_ports_unique_range_no_overlap_single_port():
    """
    arrange: A range requirer and a single-port requirer outside the range.
    act: Build HaproxyRouteTcpRequirersData.
    assert: Neither is marked invalid.
    """
    r1 = _make_requirer(1, port_range=(10500, 10600))
    r2 = _make_requirer(2, port=8080)

    data = HaproxyRouteTcpRequirersData(
        requirers_data=[r1, r2], relation_ids_with_invalid_data=set()
    )
    assert not data.relation_ids_with_invalid_data


# ---------------------------------------------------------------------------
# State: HAProxyRouteTcpBackend / HAProxyRouteTcpFrontend
# ---------------------------------------------------------------------------

from state.haproxy_route_tcp import (  # noqa: E402  (after library imports)
    HAProxyRouteTcpBackend,
    HAProxyRouteTcpFrontend,
)


def _make_backend(relation_id: int, **app_data_kwargs) -> HAProxyRouteTcpBackend:
    """Helper to build a HAProxyRouteTcpBackend."""
    requirer = _make_requirer(relation_id, **app_data_kwargs)
    return HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(requirer)


def test_backend_servers_port_range_omits_port():
    """
    arrange: A backend with port_range set.
    act: Access the servers property.
    assert: Each server has port=None.
    """
    backend = _make_backend(1, port_range=(10500, 10600))

    assert backend.servers
    for server in backend.servers:
        assert server.port is None


def test_backend_servers_single_port_retains_port():
    """
    arrange: A backend with a single port.
    act: Access the servers property.
    assert: Each server has the backend_port.
    """
    backend = _make_backend(1, port=8080, backend_port=9090)

    assert backend.servers
    for server in backend.servers:
        assert server.port == 9090


def test_backend_name_with_port_range():
    """
    arrange: A backend with port_range set.
    act: Access the name property.
    assert: Name includes the range.
    """
    backend = _make_backend(1, port_range=(10500, 10600))
    assert backend.name == "app_10500-10600"


def test_backend_name_with_single_port():
    """
    arrange: A backend with a single port.
    act: Access the name property.
    assert: Name uses the port.
    """
    backend = _make_backend(1, port=8080)
    assert backend.name == "app_8080"


def test_frontend_all_ports_single():
    """
    arrange: A HAProxyRouteTcpFrontend with a single port.
    act: Access all_ports.
    assert: Returns [port].
    """
    backend = _make_backend(1, port=8080)
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])
    assert frontend.all_ports == [8080]


def test_frontend_all_ports_range():
    """
    arrange: A HAProxyRouteTcpFrontend with a port range.
    act: Access all_ports.
    assert: Returns the full inclusive list of ports.
    """
    backend = _make_backend(1, port_range=(10500, 10503))
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])
    assert frontend.all_ports == [10500, 10501, 10502, 10503]


def test_frontend_default_backend_name_range():
    """
    arrange: A HAProxyRouteTcpFrontend with a port range.
    act: Access default_backend_name.
    assert: Name includes the range.
    """
    backend = _make_backend(1, port_range=(10500, 10600))
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])
    assert frontend.default_backend_name == "haproxy_route_tcp_10500-10600_default_backend"


def test_frontend_from_backends_port_range():
    """
    arrange: A backend with port_range.
    act: Create a frontend from it.
    assert: Frontend has correct port and port_range attributes.
    """
    backend = _make_backend(1, port_range=(10500, 10600))
    frontend = HAProxyRouteTcpFrontend.from_backends([backend])

    assert frontend.port == 10500
    assert frontend.port_range == (10500, 10600)
    assert frontend.port_range is not None


# ---------------------------------------------------------------------------
# State: parse_haproxy_route_tcp_requirers_data
# ---------------------------------------------------------------------------

from state.haproxy_route import parse_haproxy_route_tcp_requirers_data  # noqa: E402


def test_parse_tcp_requirers_data_with_port_range():
    """
    arrange: A requirer with port_range.
    act: Parse into frontends.
    assert: One frontend is created with the correct port range.
    """
    r1 = _make_requirer(1, port_range=(10500, 10600))
    data = HaproxyRouteTcpRequirersData(requirers_data=[r1], relation_ids_with_invalid_data=set())

    frontends = parse_haproxy_route_tcp_requirers_data(data)

    assert len(frontends) == 1
    assert frontends[0].port == 10500
    assert frontends[0].port_range == (10500, 10600)


def test_parse_tcp_requirers_data_range_and_single():
    """
    arrange: Two requirers: one with port_range, one with a single non-overlapping port.
    act: Parse into frontends.
    assert: Two frontends are created.
    """
    r1 = _make_requirer(1, port_range=(10500, 10600))
    r2 = _make_requirer(2, port=8080)
    data = HaproxyRouteTcpRequirersData(requirers_data=[r1, r2], relation_ids_with_invalid_data=set())

    frontends = parse_haproxy_route_tcp_requirers_data(data)
    assert len(frontends) == 2
