# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for HAProxy Route Policy state dataclass."""

from typing import Any, cast

import pytest
from pydantic import ValidationError

from state.policy import HaproxyRoutePolicyInformation


def _build_state(allowed_hosts: list[str]) -> HaproxyRoutePolicyInformation:
    """Build a valid state instance with overridable allowed hosts."""
    return HaproxyRoutePolicyInformation(
        allowed_hosts=cast(list[Any], allowed_hosts),
        admin_username="admin",
        # Ignore bandit warning as this is for testing.
        admin_password="secret",  # nosec
        secret_key="test-secret-key",
    )


@pytest.mark.parametrize(
    "allowed_hosts, expected_allowed_hosts",
    [
        pytest.param([], [], id="empty-list"),
        pytest.param(["example.com"], ["example.com"], id="single-fqdn"),
        pytest.param(
            ["example.com", "api.example.com"],
            ["example.com", "api.example.com"],
            id="multiple-fqdn",
        ),
        pytest.param(["10.0.0.10"], ["10.0.0.10"], id="ipv4-address"),
        pytest.param(["2001:db8::1"], ["2001:db8::1"], id="ipv6-address"),
    ],
)
def test_haproxy_route_policy_information_init_valid_allowed_hosts(
    allowed_hosts: list[str], expected_allowed_hosts: list[str]
):
    """
    arrange: prepare valid host inputs.
    act: initialize HaproxyRoutePolicyInformation.
    assert: initialization succeeds and normalized hosts are stored.
    """
    state = _build_state(allowed_hosts)

    assert [str(host) for host in state.allowed_hosts] == expected_allowed_hosts


@pytest.mark.parametrize(
    "allowed_hosts",
    [
        pytest.param(["invalid host"], id="space-in-host"),
        pytest.param(["http://example.com"], id="url-not-host"),
        pytest.param(["exa_mple.com"], id="underscore-in-label"),
    ],
)
def test_haproxy_route_policy_information_init_invalid_allowed_hosts(allowed_hosts: list[str]):
    """
    arrange: prepare invalid host inputs.
    act: initialize HaproxyRoutePolicyInformation.
    assert: pydantic validation error is raised.
    """
    with pytest.raises(ValidationError):
        _build_state(allowed_hosts)


@pytest.mark.parametrize(
    "field_name, field_value",
    [
        pytest.param("admin_username", None, id="missing-admin-username"),
        pytest.param("admin_password", None, id="missing-admin-password"),
        pytest.param("secret_key", None, id="missing-secret-key"),
    ],
)
def test_haproxy_route_policy_information_init_rejects_none_string_fields(
    field_name: str, field_value: None
):
    """
    arrange: build state payload with missing required string field.
    act: initialize HaproxyRoutePolicyInformation.
    assert: pydantic validation error is raised.
    """
    payload: dict[str, Any] = {
        "allowed_hosts": ["example.com"],
        "admin_username": "admin",
        # Ignore bandit warning as this is for testing.
        "admin_password": "secret",  # nosec
        "secret_key": "test-secret-key",
    }
    payload[field_name] = field_value

    with pytest.raises(ValidationError):
        HaproxyRoutePolicyInformation(**payload)


@pytest.mark.parametrize(
    "allowed_hosts, expected",
    [
        pytest.param([], {"allowed-hosts": "[]"}, id="empty"),
        pytest.param(
            ["example.com", "api.example.com"],
            {"allowed-hosts": '["example.com", "api.example.com"]'},
            id="multiple-fqdn",
        ),
    ],
)
def test_allowed_hosts_snap_configuration(allowed_hosts: list[str], expected: dict[str, str]):
    """
    arrange: initialize state with valid allowed hosts.
    act: read snap configuration property.
    assert: allowed-hosts is serialized to expected JSON string.
    """
    state = _build_state(allowed_hosts)

    assert state.allowed_hosts_snap_configuration == expected
