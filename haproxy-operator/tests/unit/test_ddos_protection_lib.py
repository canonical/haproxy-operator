# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for DDoS protection interface library."""

import pytest
from charms.haproxy.v0.ddos_protection import (
    DDoSProtectionProviderAppData,
    RateLimitPolicy,
)
from pydantic import ValidationError


def test_ddos_protection_provider_app_data_validation():
    """
    arrange: Create a DDoSProtectionProviderAppData model with valid data.
    act: Validate the model.
    assert: Model validation passes and all fields are set correctly.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=100,
        rate_limit_connections_per_minute=50,
        concurrent_connections_limit=1000,
        error_rate=10,
        limit_policy="reject",
        ip_allow_list=["192.168.1.1", "192.168.1.0/24"],
        http_request_timeout=30,
        http_keepalive_timeout=60,
        client_timeout=50,
        deny_paths=["/admin", "/internal"],
    )

    assert data.rate_limit_requests_per_minute == 100
    assert data.rate_limit_connections_per_minute == 50
    assert data.concurrent_connections_limit == 1000
    assert data.error_rate == 10
    assert data.limit_policy == RateLimitPolicy.REJECT
    assert len(data.ip_allow_list) == 2
    assert data.http_request_timeout == 30
    assert data.http_keepalive_timeout == 60
    assert data.client_timeout == 50
    assert data.deny_paths == ["/admin", "/internal"]


@pytest.mark.parametrize(
    "policy_input,expected_policy,expected_status_code",
    [
        ("deny 503", RateLimitPolicy.DENY, 503),
        ("reject", RateLimitPolicy.REJECT, None),
        ("silent-drop", RateLimitPolicy.SILENT, None),
        ("deny", RateLimitPolicy.DENY, None),
    ],
)
def test_ddos_protection_provider_app_data_with_different_policies(
    policy_input: str, expected_policy: RateLimitPolicy, expected_status_code: int | None
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with different policies and status codes.
    act: Validate the model.
    assert: Policy and status code are correctly parsed and set.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=100,
        limit_policy=policy_input,
    )

    assert data.limit_policy == expected_policy
    assert data.policy_status_code == expected_status_code


@pytest.mark.parametrize(
    "invalid_policy",
    [
        "reject 503",
        "silent-drop 503",
        "deny 99",
        "deny 600",
        "deny abc",
        "invalid-policy",
    ],
)
def test_ddos_protection_provider_app_data_status_code_with_invalid_policy(
    invalid_policy: str,
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with invalid policy.
    act: Validate the model.
    assert: Validation fails.
    """
    with pytest.raises(ValidationError):
        DDoSProtectionProviderAppData(
            rate_limit_requests_per_minute=100,
            limit_policy=invalid_policy,  # type: ignore
        )


def test_ddos_protection_provider_app_data_ip_allow_list():
    """
    arrange: Create a DDoSProtectionProviderAppData model with a mix of IPv4 addresses
    and CIDR blocks.
    act: Validate the model.
    assert: IP addresses are correctly converted and have expected values.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=100,
        ip_allow_list=["192.168.1.1", "10.0.0.0/8"],
    )

    assert len(data.ip_allow_list) == 2
    assert str(data.ip_allow_list[0]) == "192.168.1.1"
    assert str(data.ip_allow_list[1]) == "10.0.0.0/8"


def test_ddos_protection_provider_app_data_invalid_ip():
    """
    arrange: Create a DDoSProtectionProviderAppData model with invalid IP address.
    act: Validate the model.
    assert: Validation raises an error.
    """
    with pytest.raises(ValidationError):
        DDoSProtectionProviderAppData(
            rate_limit_requests_per_minute=100,
            ip_allow_list=["0.0.0"],  # type: ignore
        )


def test_ddos_protection_provider_app_data_deny_paths_empty_string():
    """
    arrange: Create a DDoSProtectionProviderAppData model with empty string in deny_paths.
    act: Validate the model.
    assert: Validation raises an error.
    """
    with pytest.raises(ValidationError):
        DDoSProtectionProviderAppData(
            rate_limit_requests_per_minute=100,
            deny_paths=["/admin", ""],  # type: ignore
        )


def test_ddos_protection_provider_app_data_empty():
    """
    arrange: Create a DDoSProtectionProviderAppData model with no arguments.
    act: Validate the model.
    assert: Model validation passes with the default limit policy.
    """
    data = DDoSProtectionProviderAppData()
    assert data.limit_policy == RateLimitPolicy.SILENT
