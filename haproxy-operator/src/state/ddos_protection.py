# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy charm DDoS protection information."""

import logging
from typing import Optional

from charms.haproxy.v0.ddos_protection import (
    DDoSProtectionInvalidRelationDataError,
    DDoSProtectionRequirer,
)
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class DDosProtectionValidationError(CharmStateValidationBaseError):
    """Exception raised when validation of DDoS protection state failed."""


@dataclass(frozen=True)
class DDosProtection:
    """A component of charm state containing DDoS protection configuration.

    Attributes:
        rate_limit_requests_per_minute: Maximum number of requests per minute.
        rate_limit_connections_per_minute: Maximum number of connections per minute.
        concurrent_connections_limit: Maximum number of concurrent connections.
        error_rate: Number of errors per minute to trigger the limit policy.
        limit_policy_http: HTTP policy to be applied when HTTP-level limits are exceeded.
        limit_policy_tcp: TCP policy to be applied when TCP-level limits are exceeded.
        policy_status_code: HTTP status code for deny policy.
        http_request_timeout: Timeout for HTTP requests in seconds.
        http_keepalive_timeout: Timeout for HTTP keep-alive connections in seconds.
        client_timeout: Timeout for client connections in seconds.
        ip_allow_list_file_path: Path to the file containing the IP allow list.
        deny_paths_file_path: Path to the file containing the deny paths list.
    """

    rate_limit_requests_per_minute: Optional[int] = None
    rate_limit_connections_per_minute: Optional[int] = None
    concurrent_connections_limit: Optional[int] = None
    error_rate: Optional[int] = None
    limit_policy_http: Optional[str] = None
    limit_policy_tcp: Optional[str] = None
    policy_status_code: Optional[int] = None
    http_request_timeout: Optional[int] = None
    http_keepalive_timeout: Optional[int] = None
    client_timeout: Optional[int] = None
    ip_allow_list: Optional[list[str]] = None
    deny_paths: Optional[list[str]] = None

    @property
    def has_rate_limiting(self) -> bool:
        """Check if rate limiting should be applied.

        Returns True if at least one of the rate limits is configured.
        """
        return bool(
            (self.limit_policy_http and (self.error_rate or self.rate_limit_requests_per_minute))
            or (
                self.limit_policy_tcp
                and (self.rate_limit_connections_per_minute or self.concurrent_connections_limit)
            )
        )

    @classmethod
    def from_charm(
        cls,
        ddos_requirer: DDoSProtectionRequirer,
    ) -> "DDosProtection":
        """Get DDoS protection configuration from charm's ddos-protection relation.
        Convert timeouts from seconds to milliseconds.

        Args:
            ddos_requirer: The DDoSProtectionRequirer instance from the charm.

        Raises:
            DDosProtectionValidationError: When validation of the state component failed.

        Returns:
            DDosProtection: DDoS protection configuration.
        """
        try:
            config = ddos_requirer.get_ddos_config()
            if not config:
                return cls()

            http_request_timeout = (
                config.http_request_timeout * 1000 if config.http_request_timeout else None
            )
            http_keepalive_timeout = (
                config.http_keepalive_timeout * 1000 if config.http_keepalive_timeout else None
            )
            client_timeout = config.client_timeout * 1000 if config.client_timeout else None

            http_limit_policy_str = (
                config.limit_policy_http.value if config.limit_policy_http else None
            )
            tcp_limit_policy_str = (
                config.limit_policy_tcp.value if config.limit_policy_tcp else None
            )

            return cls(
                rate_limit_requests_per_minute=config.rate_limit_requests_per_minute,
                rate_limit_connections_per_minute=config.rate_limit_connections_per_minute,
                concurrent_connections_limit=config.concurrent_connections_limit,
                error_rate=config.error_rate,
                limit_policy_http=http_limit_policy_str,
                limit_policy_tcp=tcp_limit_policy_str,
                policy_status_code=config.policy_status_code,
                http_request_timeout=http_request_timeout,
                http_keepalive_timeout=http_keepalive_timeout,
                client_timeout=client_timeout,
                ip_allow_list=[str(ip) for ip in config.ip_allow_list]
                if config.ip_allow_list
                else None,
                deny_paths=config.deny_paths,
            )

        except (DDosProtectionValidationError, DDoSProtectionInvalidRelationDataError) as e:
            logger.error("Failed to load DDoS protection configuration: %s", str(e))
            raise DDosProtectionValidationError(
                f"Failed to load DDoS protection configuration: {e}"
            ) from e
