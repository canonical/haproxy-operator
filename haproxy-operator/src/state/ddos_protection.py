# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy charm DDoS protection information."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from charms.haproxy.v0.ddos_protection import (
    DDoSProtectionInvalidRelationDataError,
    DDoSProtectionProviderAppData,
    DDoSProtectionRequirer,
    RateLimitPolicy,
)
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError
from .haproxy_route import HaproxyRouteRequirersInformation

if TYPE_CHECKING:
    from .ingress import IngressRequirersInformation
    from .ingress_per_unit import IngressPerUnitRequirersInformation

logger = logging.getLogger(__name__)

IP_ALLOW_LIST_FILE = Path("/var/lib/haproxy/ip_allow_list.lst")
DENY_PATHS_FILE = Path("/var/lib/haproxy/deny_paths.lst")


def _is_http_mode(
    requirer_info: Union[
        "HaproxyRouteRequirersInformation",
        "IngressRequirersInformation",
        "IngressPerUnitRequirersInformation",
    ],
) -> bool:
    """Check if the given requirer information represents HTTP-based mode.

    Args:
        requirer_info: The requirer information object to check.

    Returns:
        True if the mode is HTTP-based. For HaproxyRouteRequirersInformation,
        returns True only if no tcp_endpoints are configured.
    """
    if isinstance(requirer_info, HaproxyRouteRequirersInformation):
        return not requirer_info.tcp_endpoints
    return True


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
        limit_policy: Policy to be applied when limits are exceeded.
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
    limit_policy: Optional[str] = None
    policy_status_code: Optional[int] = None
    http_request_timeout: Optional[int] = None
    http_keepalive_timeout: Optional[int] = None
    client_timeout: Optional[int] = None
    ip_allow_list_file_path: Optional[Path] = None
    deny_paths_file_path: Optional[Path] = None

    @property
    def has_rate_limiting(self) -> bool:
        """Check if rate limiting should be applied.

        Returns True if limit_policy is set AND at least one rate limiting metric is configured.
        """
        return bool(
            self.limit_policy
            and (
                self.rate_limit_connections_per_minute
                or self.concurrent_connections_limit
                or self.error_rate
                or self.rate_limit_requests_per_minute
            )
        )

    @staticmethod
    def _store_config_to_file(data: Optional[list[str]], file_path: Path) -> Optional[Path]:
        """Store configuration data to a file.

        Args:
            data: The data to store.
            file_path: Path to the file where data will be stored.

        Returns:
            Path to the file if data is present, None otherwise.
        """
        if not data:
            file_path.unlink(missing_ok=True)
            logger.debug("Removed DDoS configuration file %s (no data)", file_path)
            return None

        lines = [str(item).strip() for item in data if str(item).strip()]
        content = "\n".join(lines) + "\n"

        file_path.write_text(content, encoding="utf-8")

        logger.debug(
            "Stored DDoS configuration to %s with %d entries",
            file_path,
            len(lines),
        )

        return file_path

    @staticmethod
    def _get_limit_policy(
        config: DDoSProtectionProviderAppData, is_http_mode: bool
    ) -> Optional[str]:
        """Get the appropriate limit policy for the given mode.

        For TCP modes, "deny" policy is not valid.
        Only "reject" and "silent-drop" are valid for TCP.

        Args:
            config: The DDoS protection configuration object.
            is_http_mode: Whether the mode is HTTP-based.

        Returns:
            The limit policy value as string, or None if not applicable.

        Raises:
            DDosProtectionValidationError: When "deny" policy is used in TCP mode.
        """
        if not config.limit_policy:
            return None

        limit_policy_str = config.limit_policy.value

        if not is_http_mode and config.limit_policy == RateLimitPolicy.DENY:
            raise DDosProtectionValidationError(
                "'deny' policy is not supported when TCP endpoints are configured; "
                "use 'reject' or 'silent-drop' instead."
            )

        return limit_policy_str

    @classmethod
    def from_charm(
        cls,
        ddos_requirer: DDoSProtectionRequirer,
        requirer_info: Union[
            "HaproxyRouteRequirersInformation",
            "IngressRequirersInformation",
            "IngressPerUnitRequirersInformation",
        ],
    ) -> "DDosProtection":
        """Get DDoS protection configuration from charm's ddos-protection relation.

        Args:
            ddos_requirer: The DDoSProtectionRequirer instance from the charm.
            requirer_info: The requirer information to determine if TCP endpoints are configured.

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

            is_http_mode = _is_http_mode(requirer_info)
            limit_policy_str = cls._get_limit_policy(config, is_http_mode)

            ip_allow_list_file_path = cls._store_config_to_file(
                config.ip_allow_list, IP_ALLOW_LIST_FILE
            )
            deny_paths_file_path = cls._store_config_to_file(config.deny_paths, DENY_PATHS_FILE)

            return cls(
                rate_limit_requests_per_minute=config.rate_limit_requests_per_minute,
                rate_limit_connections_per_minute=config.rate_limit_connections_per_minute,
                concurrent_connections_limit=config.concurrent_connections_limit,
                error_rate=config.error_rate,
                limit_policy=limit_policy_str,
                policy_status_code=config.policy_status_code,
                http_request_timeout=http_request_timeout,
                http_keepalive_timeout=http_keepalive_timeout,
                client_timeout=client_timeout,
                ip_allow_list_file_path=ip_allow_list_file_path,
                deny_paths_file_path=deny_paths_file_path,
            )

        except (DDosProtectionValidationError, DDoSProtectionInvalidRelationDataError) as e:
            logger.error("Failed to load DDoS protection configuration: %s", str(e))
            raise DDosProtectionValidationError(
                f"Failed to load DDoS protection configuration: {e}"
            ) from e
