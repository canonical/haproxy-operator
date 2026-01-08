# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy DDoS protection configurator charm state."""

import itertools
import logging
from typing import List, Optional, Set, cast

import ops
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass

logger = logging.getLogger()


class InvalidDDoSProtectionConfigError(Exception):
    """Exception raised when DDoS protection configuration is invalid."""


@dataclass(frozen=True)
class CharmState:
    """DDoS protection configuration state.

    Attributes:
        rate_limit_requests_per_minute: Maximum number of requests per minute per entry.
        rate_limit_connections_per_minute: Maximum number of connections per minute per entry.
        concurrent_connections_limit: Maximum number of concurrent connections per entry.
        error_rate_per_minute: Number of errors per minute per entry to trigger the limit policy.
        limit_policy: Policy to be applied when limits are exceeded.
        ip_allow_list: Comma-separated list of IPv4 addresses or CIDR blocks to be allowed.
        http_request_timeout: Timeout for HTTP requests in seconds.
        http_keepalive_timeout: Timeout for HTTP keep-alive connections in seconds.
        client_timeout: Timeout for client connections in seconds.
        deny_paths: Comma-separated list of paths to deny.
    """

    rate_limit_requests_per_minute: Optional[int] = Field(default=None)
    rate_limit_connections_per_minute: Optional[int] = Field(default=None)
    concurrent_connections_limit: Optional[int] = Field(default=None)
    error_rate_per_minute: Optional[int] = Field(default=None)
    limit_policy: Optional[str] = Field(default=None)
    ip_allow_list: Optional[List[str]] = Field(default=None)
    http_request_timeout: Optional[int] = Field(default=None)
    http_keepalive_timeout: Optional[int] = Field(default=None)
    client_timeout: Optional[int] = Field(default=None)
    deny_paths: Optional[List[str]] = Field(default=None)

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmState":
        """Create a CharmState instance from the charm configuration.

        Args:
            charm: The charm instance.

        Raises:
            InvalidDDoSProtectionConfigError: When the charm configuration is invalid.

        Returns:
            CharmState: The charm state instance.
        """
        config = charm.config

        try:
            rate_limit_requests_per_minute = cast(
                Optional[int], config.get("rate-limit-requests-per-minute")
            )
            rate_limit_connections_per_minute = cast(
                Optional[int], config.get("rate-limit-connections-per-minute")
            )
            concurrent_connections_limit = cast(
                Optional[int], config.get("concurrent-connections-limit")
            )
            error_rate_per_minute = cast(Optional[int], config.get("error-rate-per-minute"))
            limit_policy = cast(Optional[str], config.get("limit-policy"))
            ip_allow_list: Optional[list[str]] = (
                [ip.strip() for ip in cast(str, config.get("ip-allow-list", "")).split(",")]
                if config.get("ip-allow-list")
                else None
            )
            http_request_timeout = cast(Optional[int], config.get("http-request-timeout"))
            http_keepalive_timeout = cast(Optional[int], config.get("http-keepalive-timeout"))
            client_timeout = cast(Optional[int], config.get("client-timeout"))
            deny_paths: Optional[list[str]] = (
                [path.strip() for path in cast(str, config.get("deny-paths", "")).split(",")]
                if config.get("deny-paths")
                else None
            )

            return cls(
                rate_limit_requests_per_minute=rate_limit_requests_per_minute,
                rate_limit_connections_per_minute=rate_limit_connections_per_minute,
                concurrent_connections_limit=concurrent_connections_limit,
                error_rate_per_minute=error_rate_per_minute,
                limit_policy=limit_policy,
                ip_allow_list=ip_allow_list,
                http_request_timeout=http_request_timeout,
                http_keepalive_timeout=http_keepalive_timeout,
                client_timeout=client_timeout,
                deny_paths=deny_paths,
            )

        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidDDoSProtectionConfigError(
                f"invalid configuration: {error_field_str}"
            ) from exc


def get_invalid_config_fields(exc: ValidationError) -> Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc: The validation error exception.

    Returns:
        str: list of fields that failed validation.
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
