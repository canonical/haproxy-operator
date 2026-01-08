# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the charm state module."""

from unittest.mock import MagicMock

import pytest

from state import CharmState, InvalidDDoSProtectionConfigError


def test_charm_state_from_charm_with_validation_error():
    """
    arrange: Create a mock charm with invalid config.
    act: Call CharmState.from_charm().
    assert: InvalidDDoSProtectionConfigError is raised with field name in message.
    """
    mock_charm = MagicMock()
    mock_charm.config.get = MagicMock(
        side_effect=lambda key, default=None: {
            "error-rate-per-minute": "ABC",
        }.get(key, default)
    )

    with pytest.raises(InvalidDDoSProtectionConfigError) as exc_info:
        CharmState.from_charm(mock_charm)
        assert "error-rate-per-minute" in str(exc_info.value)


def test_charm_state_from_charm_successful():
    """
    arrange: Create a charm with valid config.
    act: Call CharmState.from_charm().
    assert: CharmState instance is created successfully.
    """
    mock_charm = MagicMock()
    mock_charm.config.get = MagicMock(
        side_effect=lambda key, default=None: {
            "rate-limit-requests-per-minute": 100,
            "rate-limit-connections-per-minute": None,
            "concurrent-connections-limit": None,
            "error-rate-per-minute": None,
            "limit-policy": "reject",
            "ip-allow-list": "192.168.1.1, 10.0.0.0/8",
            "http-request-timeout": 30,
            "http-keepalive-timeout": 60,
            "client-timeout": 50,
            "deny-paths": "/admin, /internal",
        }.get(key, default)
    )

    state = CharmState.from_charm(mock_charm)

    assert state.rate_limit_requests_per_minute == 100
    assert state.limit_policy == "reject"
    assert state.ip_allow_list == ["192.168.1.1", "10.0.0.0/8"]
    assert state.deny_paths == ["/admin", "/internal"]


def test_charm_state_from_charm_with_empty_config():
    """
    arrange: Create a charm with empty config.
    act: Call CharmState.from_charm().
    assert: CharmState instance is created with all None values.
    """
    mock_charm = MagicMock()
    mock_charm.config.get = MagicMock(return_value=None)

    state = CharmState.from_charm(mock_charm)

    assert state.rate_limit_requests_per_minute is None
    assert state.rate_limit_connections_per_minute is None
    assert state.concurrent_connections_limit is None
    assert state.error_rate_per_minute is None
    assert state.limit_policy is None
    assert state.ip_allow_list is None
    assert state.http_request_timeout is None
    assert state.http_keepalive_timeout is None
    assert state.client_timeout is None
    assert state.deny_paths is None
