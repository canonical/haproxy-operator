# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DDoS protection interface data models.

This library is internal to the haproxy-operator monorepo and defines the
data model exchanged through the ``ddos-protection`` relation.

The provider charm saves a :class:`DDoSProtectionProviderAppData` instance to
the relation with ``Relation.save`` and the requirer charm loads it with
``Relation.load``.
"""

from enum import Enum
from ipaddress import ip_address, ip_network
from typing import Optional, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    IPvAnyAddress,
    IPvAnyNetwork,
    field_validator,
    model_validator,
)
from typing_extensions import Self

DDOS_PROTECTION_RELATION_NAME = "ddos-protection"


class HttpRateLimitPolicy(Enum):
    """Enum of possible HTTP rate limiting policies.

    Attrs:
        DENY: Deny the connection.
        REJECT: Send a TCP reset packet to close the connection.
        SILENT: disconnects immediately without notifying the client
            that the connection has been closed (no packet sent).
    """

    DENY = "deny"
    REJECT = "reject"
    SILENT = "silent-drop"


class TcpRateLimitPolicy(Enum):
    """Enum of possible TCP rate limiting policies.

    Attrs:
        REJECT: Send a TCP reset packet to close the connection.
        SILENT: disconnects immediately without notifying the client
            that the connection has been closed (no packet sent).
    """

    REJECT = "reject"
    SILENT = "silent-drop"


class DDoSProtectionProviderAppData(BaseModel):
    """Configuration model for DDoS protection provider.

    Attributes:
        rate_limit_requests_per_minute: Maximum number of requests per minute per entry.
        rate_limit_connections_per_minute: Maximum number of connections per minute per entry.
        concurrent_connections_limit: Maximum number of concurrent connections per entry.
        error_rate: Number of errors per minute per entry to trigger the limit policy.
        limit_policy_http: Policy to be applied when HTTP-level limits are exceeded.
        limit_policy_tcp: Policy to be applied when TCP-level limits are exceeded.
        policy_status_code: HTTP status code for deny policy (only set when limit_policy_http is deny).
        ip_allow_list: List of IP addresses or CIDR blocks to be allowed.
        http_request_timeout: Timeout for HTTP requests in seconds.
        http_keepalive_timeout: Timeout for HTTP keep-alive connections in seconds.
        client_timeout: Timeout for client connections in seconds.
        deny_paths: List of paths to deny.
    """

    model_config = ConfigDict(extra="ignore")

    rate_limit_requests_per_minute: Optional[int] = Field(default=None, gt=0)
    rate_limit_connections_per_minute: Optional[int] = Field(default=None, gt=0)
    concurrent_connections_limit: Optional[int] = Field(default=None, gt=0)
    error_rate: Optional[int] = Field(default=None, gt=0)
    limit_policy_http: Optional[HttpRateLimitPolicy] = Field(default=None)
    limit_policy_tcp: Optional[TcpRateLimitPolicy] = Field(default=None)
    policy_status_code: Optional[int] = Field(default=None, ge=100, le=599)
    ip_allow_list: Optional[list[IPvAnyAddress | IPvAnyNetwork]] = Field(default=None)
    http_request_timeout: Optional[int] = Field(default=None, gt=0)
    http_keepalive_timeout: Optional[int] = Field(default=None, gt=0)
    client_timeout: Optional[int] = Field(default=None, gt=0)
    deny_paths: Optional[list[str]] = Field(default=None)

    @field_validator("ip_allow_list", mode="before")
    @classmethod
    def validate_ip_allow_list(
        cls, v: Optional[list[str]]
    ) -> Optional[list[IPvAnyAddress | IPvAnyNetwork]]:
        """Validate and convert IP allow list.

        Converts each string to either an IP address or a network.

        Args:
            v: The list of IP addresses or CIDR blocks as strings.

        Returns:
            The list of converted IP address or network objects.
        """
        if v is None:
            return None

        return [ip_network(ip_str) if "/" in ip_str else ip_address(ip_str) for ip_str in v]

    @field_validator("deny_paths", mode="after")
    @classmethod
    def validate_deny_paths(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate that deny_paths contains no empty strings.

        Args:
            v: The validated list of paths.

        Raises:
            ValueError: When entries are empty strings.

        Returns:
            The validated list of paths.
        """
        if v is None:
            return None

        for path in v:
            if not path.strip():
                raise ValueError("Paths cannot be empty strings")

        return v

    @model_validator(mode="before")
    def validate_limit_policies(self) -> Self:
        """Validate and convert the limit_policy_http and limit_policy_tcp parameters.

        The limit_policy_http must be one of: silent-drop, reject, or deny.
        The limit_policy_tcp must be one of: silent-drop or reject.
        For deny, optionally an HTTP status code can be appended (e.g., "deny 503").
        Extracts and stores the status code separately in policy_status_code.

        Raises:
            ValueError: When limit policies are invalid.

        Returns:
            The validated model.
        """
        data = cast(dict, self)

        if data.get("limit_policy_http"):
            limit_policy_http = data["limit_policy_http"]
            parts = limit_policy_http.strip().split()
            policy_str = parts[0]

            try:
                http_policy = HttpRateLimitPolicy(policy_str)
            except ValueError:
                valid_policies = ", ".join(p.value for p in HttpRateLimitPolicy)
                raise ValueError(
                    f"Invalid limit_policy_http: '{policy_str}'. Must be one of: {valid_policies}"
                )

            if http_policy != HttpRateLimitPolicy.DENY and len(parts) > 1:
                raise ValueError("Status code can only be specified with 'deny' policy")

            if http_policy == HttpRateLimitPolicy.DENY and len(parts) > 1:
                try:
                    status_code = int(parts[1])
                    data["policy_status_code"] = status_code
                except ValueError as e:
                    raise ValueError(
                        f"Invalid limit_policy_http format. Expected 'deny' or 'deny <status_code>', "
                        f"got '{limit_policy_http}'"
                    ) from e

            data["limit_policy_http"] = http_policy

        if data.get("limit_policy_tcp"):
            limit_policy_tcp = data["limit_policy_tcp"].strip()

            try:
                tcp_policy = TcpRateLimitPolicy(limit_policy_tcp)
            except ValueError:
                valid_policies = ", ".join(p.value for p in TcpRateLimitPolicy)
                raise ValueError(
                    f"Invalid limit_policy_tcp: '{limit_policy_tcp}'. Must be one of: {valid_policies}"
                )

            data["limit_policy_tcp"] = tcp_policy

        return self

    @model_validator(mode="after")
    def validate_limit_policies_with_rate_limits(self) -> Self:
        """Validate that limit policies are only set when corresponding rate limits are configured.

        HTTP policy applies to: rate_limit_requests_per_minute, error_rate
        TCP policy applies to: rate_limit_connections_per_minute, concurrent_connections_limit
        Sets default policies to SILENT when rate limits are present but policies are not set.

        Raises:
            ValueError: When limit policies are set without corresponding rate limits.

        Returns:
            The validated model.
        """
        has_http_rate_limit = any(
            [
                self.rate_limit_requests_per_minute,
                self.error_rate,
            ]
        )

        has_tcp_rate_limit = any(
            [
                self.rate_limit_connections_per_minute,
                self.concurrent_connections_limit,
            ]
        )

        if not has_http_rate_limit and self.limit_policy_http is not None:
            raise ValueError(
                "limit_policy_http can only be set if at least one of "
                "rate_limit_requests_per_minute or error_rate is set"
            )

        if not has_tcp_rate_limit and self.limit_policy_tcp is not None:
            raise ValueError(
                "limit_policy_tcp can only be set if at least one of "
                "rate_limit_connections_per_minute or concurrent_connections_limit is set"
            )

        if has_http_rate_limit and self.limit_policy_http is None:
            object.__setattr__(self, "limit_policy_http", HttpRateLimitPolicy.SILENT)

        if has_tcp_rate_limit and self.limit_policy_tcp is None:
            object.__setattr__(self, "limit_policy_tcp", TcpRateLimitPolicy.SILENT)

        return self
