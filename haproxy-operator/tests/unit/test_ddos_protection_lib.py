# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for DDoS protection interface library."""

import pytest
from charms.haproxy.v0.ddos_protection import (
    DDoSProtectionProviderAppData,
    HttpRateLimitPolicy,
    TcpRateLimitPolicy,
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
        limit_policy_http="deny 503",
        limit_policy_tcp="reject",
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
    assert data.limit_policy_http == HttpRateLimitPolicy.DENY
    assert data.policy_status_code == 503
    assert data.limit_policy_tcp == TcpRateLimitPolicy.REJECT
    assert len(data.ip_allow_list) == 2
    assert data.http_request_timeout == 30
    assert data.http_keepalive_timeout == 60
    assert data.client_timeout == 50
    assert data.deny_paths == ["/admin", "/internal"]


@pytest.mark.parametrize(
    "http_policy_input,expected_http_policy,expected_status_code",
    [
        ("deny 503", HttpRateLimitPolicy.DENY, 503),
        ("reject", HttpRateLimitPolicy.REJECT, None),
        ("silent-drop", HttpRateLimitPolicy.SILENT, None),
        ("deny", HttpRateLimitPolicy.DENY, None),
    ],
)
def test_ddos_protection_provider_app_data_with_different_http_policies(
    http_policy_input: str,
    expected_http_policy: HttpRateLimitPolicy,
    expected_status_code: int | None,
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with different policies and status codes.
    act: Validate the model.
    assert: Policy and status code are correctly parsed and set.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=100,
        limit_policy_http=http_policy_input,
    )

    assert data.limit_policy_http == expected_http_policy
    assert data.policy_status_code == expected_status_code


@pytest.mark.parametrize(
    "invalid_http_policy",
    [
        "reject 503",
        "silent-drop 503",
        "deny 99",
        "deny 600",
        "deny abc",
        "invalid-policy",
    ],
)
def test_ddos_protection_provider_app_data_status_code_with_invalid_http_policy(
    invalid_http_policy: str,
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with invalid HTTP policy.
    act: Validate the model.
    assert: Validation fails.
    """
    with pytest.raises(ValidationError):
        DDoSProtectionProviderAppData(
            rate_limit_requests_per_minute=100,
            limit_policy_http=invalid_http_policy,  # type: ignore
        )


@pytest.mark.parametrize(
    "tcp_policy_input,expected_tcp_policy",
    [
        ("reject", TcpRateLimitPolicy.REJECT),
        ("silent-drop", TcpRateLimitPolicy.SILENT),
    ],
)
def test_ddos_protection_provider_app_data_with_different_tcp_policies(
    tcp_policy_input: str, expected_tcp_policy: TcpRateLimitPolicy
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with different TCP policies.
    act: Validate the model.
    assert: TCP Policy is correctly parsed and set.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_connections_per_minute=50,
        limit_policy_tcp=tcp_policy_input,
    )

    assert data.limit_policy_tcp == expected_tcp_policy


@pytest.mark.parametrize(
    "invalid_tcp_policy",
    [
        "deny",  # deny not allowed for TCP
        "deny 503",  # deny with status code not allowed for TCP
        "reject 503",  # status codes not allowed for TCP
        "silent-drop 503",  # status codes not allowed for TCP
        "invalid-policy",
    ],
)
def test_ddos_protection_provider_app_data_with_invalid_tcp_policy(
    invalid_tcp_policy: str,
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with invalid TCP policy.
    act: Validate the model.
    assert: Validation fails.
    """
    with pytest.raises(ValidationError):
        DDoSProtectionProviderAppData(
            rate_limit_connections_per_minute=50,
            limit_policy_tcp=invalid_tcp_policy,  # type: ignore
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
        ip_allow_list=["192.168.0.0/16", "10.0.0.0/8"],
    )

    assert len(data.ip_allow_list) == 2
    assert str(data.ip_allow_list[0]) == "192.168.0.0/16"
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


def test_ddos_protection_provider_app_data_http_limit_policy_requires_rate_limits():
    """
    arrange: Create a DDoSProtectionProviderAppData model with HTTP limit_policy but no HTTP rate limits.
    act: Validate the model.
    assert: Validation fails with appropriate error.
    """
    with pytest.raises(ValidationError, match="limit_policy_http can only be set"):
        DDoSProtectionProviderAppData(
            limit_policy_http="reject",
        )


def test_ddos_protection_provider_app_data_rate_limit_defaults_policy_to_silent():
    """
    arrange: Create a DDoSProtectionProviderAppData model with both HTTP and TCP rate limits but no policies.
    act: Validate the model.
    assert: Both limit_policies are automatically set to SILENT.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=100,
        rate_limit_connections_per_minute=50,
    )
    assert data.limit_policy_http == HttpRateLimitPolicy.SILENT
    assert data.limit_policy_tcp == TcpRateLimitPolicy.SILENT


@pytest.mark.parametrize(
    "rate_limit_field,rate_limit_value,expected_http_policy,expected_tcp_policy",
    [
        ("rate_limit_requests_per_minute", 100, HttpRateLimitPolicy.SILENT, None),
        ("rate_limit_connections_per_minute", 50, None, TcpRateLimitPolicy.SILENT),
        ("concurrent_connections_limit", 1000, None, TcpRateLimitPolicy.SILENT),
        ("error_rate", 10, HttpRateLimitPolicy.SILENT, None),
    ],
)
def test_ddos_protection_provider_app_data_any_rate_limit_defaults_policy(
    rate_limit_field: str, rate_limit_value: int, expected_http_policy, expected_tcp_policy
):
    """
    arrange: Create a DDoSProtectionProviderAppData model with each type of rate limit.
    act: Validate the model.
    assert: limit_policy is automatically set to SILENT for the appropriate policy type.
    """
    data = DDoSProtectionProviderAppData(**{rate_limit_field: rate_limit_value})
    assert data.limit_policy_http == expected_http_policy
    assert data.limit_policy_tcp == expected_tcp_policy


def test_ddos_protection_provider_app_data_tcp_limit_policy_requires_rate_limits():
    """
    arrange: Create a DDoSProtectionProviderAppData model with TCP limit_policy but no TCP rate limits.
    act: Validate the model.
    assert: Validation fails with appropriate error.
    """
    with pytest.raises(ValidationError, match="limit_policy_tcp can only be set"):
        DDoSProtectionProviderAppData(
            limit_policy_tcp="reject",
        )
