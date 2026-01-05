"""DDoS protection interface library.

## Getting Started

To get started using the library, you need to first declare the library in
the charm-libs section of your `charmcraft.yaml` file:

```yaml
charm-libs:
- lib: haproxy.ddos_protection
  version: "0"
```

Then, fetch the library using `charmcraft`:

```shell
cd some-charm
charmcraft fetch-libs
```

## Using the library as the Provider

The provider charm should expose the interface as shown below:

```yaml
provides:
    ddos-protection:
        interface: ddos-protection
```

Then, to initialise the library:

```python
from charms.haproxy.v0.ddos_protection import DDoSProtectionProvider

class DDoSConfigurator(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.ddos_provider = DDoSProtectionProvider(self)
        # Set the configuration when ready
        self.ddos_provider.set_config(
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
```

## Using the library as the Requirer

The requirer charm should expose the interface as shown below:

```yaml
requires:
    ddos-protection:
        interface: ddos-protection
```

Then, to initialise the library:

```python
from charms.haproxy.v0.ddos_protection import DDoSProtectionRequirer

class HaproxyCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.ddos_requirer = DDoSProtectionRequirer(self, relation_name="ddos-protection")

        self.framework.observe(
            self.on.config_changed, self._on_config_changed
        )

    def _on_config_changed(self, event):
        # Read DDoS protection configuration
        config = self.ddos_requirer.get_ddos_config()
        if config:
            # Apply the configuration
            ...
"""

import json
import logging
from collections.abc import MutableMapping
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from typing import Optional, cast

from ops import CharmBase
from ops.framework import Object
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from typing_extensions import Self

# The unique Charmhub library identifier, never change it
LIBID = "c770645db3fb4ce59a68eb52089f6766"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

logger = logging.getLogger(__name__)
DDOS_PROTECTION_RELATION_NAME = "ddos-protection"


class DataValidationError(Exception):
    """Raised when data validation fails."""


class DDoSProtectionInvalidRelationDataError(Exception):
    """Raised when data validation of the ddos-protection relation fails."""


class _DatabagModel(BaseModel):
    """Base databag model.

    Attrs:
        model_config: pydantic model configuration.
    """

    model_config = ConfigDict(
        # tolerate additional keys in databag
        extra="ignore",
        # Allow instantiating this class by field name (instead of forcing alias).
        populate_by_name=True,
    )  # type: ignore
    """Pydantic config."""

    @classmethod
    def load(cls, databag: MutableMapping[str, str]) -> Self:
        """Load this model from a Juju json databag.

        Args:
            databag: Databag content.

        Raises:
            DataValidationError: When model validation failed.

        Returns:
            Self: The validated model.
        """
        try:
            data = {
                k: json.loads(v)
                for k, v in databag.items()
                # Don't attempt to parse model-external values
                if k in {(f.alias or n) for n, f in cls.model_fields.items()}
            }
        except json.JSONDecodeError as e:
            msg = f"invalid databag contents: expecting json. {databag}"
            logger.error(msg)
            raise DataValidationError(msg) from e

        try:
            return cls.model_validate_json(json.dumps(data))
        except ValidationError as e:
            msg = f"failed to validate databag: {databag}"
            logger.error(msg)
            raise DataValidationError(msg) from e

    def dump(self, databag: MutableMapping[str, str], clear: bool = True) -> None:
        """Write the contents of this model to Juju databag.

        Args:
            databag: The databag to write to.
            clear: Whether to clear the databag before writing.
        """
        if clear:
            databag.clear()

        dct = self.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        databag.update({k: json.dumps(v) for k, v in dct.items()})


class RateLimitPolicy(Enum):
    """Enum of possible rate limiting policies.

    Attrs:
        DENY: Deny the connection.
        REJECT: Send a TCP reset packet to close the connection.
        SILENT: disconnects immediately without notifying the client
            that the connection has been closed (no packet sent).
    """

    DENY = "deny"
    REJECT = "reject"
    SILENT = "silent-drop"


class DDoSProtectionProviderAppData(_DatabagModel):
    """Configuration model for DDoS protection provider.

    Attributes:
        rate_limit_requests_per_minute: Maximum number of requests per minute per entry.
        rate_limit_connections_per_minute: Maximum number of connections per minute per entry.
        concurrent_connections_limit: Maximum number of concurrent connections per entry.
        error_rate: Number of errors per minute per entry to trigger the limit policy.
        limit_policy: Policy to be applied when limits are exceeded.
        policy_status_code: HTTP status code for deny policy (only set when limit_policy is deny).
        ip_allow_list: List of IPv4 addresses or CIDR blocks to be allowed.
        http_request_timeout: Timeout for HTTP requests in seconds.
        http_keepalive_timeout: Timeout for HTTP keep-alive connections in seconds.
        client_timeout: Timeout for client connections in seconds.
        deny_paths: List of paths to deny.
    """

    rate_limit_requests_per_minute: Optional[int] = Field(default=None, gt=0)
    rate_limit_connections_per_minute: Optional[int] = Field(default=None, gt=0)
    concurrent_connections_limit: Optional[int] = Field(default=None, gt=0)
    error_rate: Optional[int] = Field(default=None, gt=0)
    limit_policy: Optional[RateLimitPolicy] = Field(default=RateLimitPolicy.SILENT)
    policy_status_code: Optional[int] = Field(default=None, ge=100, le=599)
    ip_allow_list: Optional[list[IPv4Network | IPv4Address]] = Field(default=None)
    http_request_timeout: Optional[int] = Field(default=None, gt=0)
    http_keepalive_timeout: Optional[int] = Field(default=None, gt=0)
    client_timeout: Optional[int] = Field(default=None, gt=0)
    deny_paths: Optional[list[str]] = Field(default=None)

    @field_validator("ip_allow_list", mode="before")
    @classmethod
    def validate_ip_allow_list(
        cls, v: Optional[list[str]]
    ) -> Optional[list[IPv4Network | IPv4Address]]:
        """Validate and convert IP allow list.

        Converts each string to either IPv4Address (for single IPs) or IPv4Network (for CIDR blocks).

        Args:
            v: The list of IP addresses or CIDR blocks as strings.

        Returns:
            The list of converted IPv4Address or IPv4Network objects.
        """
        if v is None:
            return None

        return [IPv4Network(ip_str) if "/" in ip_str else IPv4Address(ip_str) for ip_str in v]

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
    def validate_limit_policy(self) -> Self:
        """Validate and convert the limit_policy parameter.

        The limit_policy must be one of: silent-drop, reject, or deny.
        For deny, optionally an HTTP status code can be appended (e.g., "deny 503").
        Extracts and stores the status code separately in policy_status_code.

        Raises:
            ValueError: When limit_policy is invalid.

        Returns:
            The validated model.
        """
        data = cast(dict, self)
        if not data.get("limit_policy"):
            return self

        limit_policy_input = data["limit_policy"]

        parts = limit_policy_input.strip().split()
        policy_str = parts[0]

        try:
            policy = RateLimitPolicy(policy_str)
        except ValueError:
            valid_policies = ", ".join(p.value for p in RateLimitPolicy)
            raise ValueError(
                f"Invalid limit_policy: '{policy_str}'. Must be one of: {valid_policies}"
            )

        if policy != RateLimitPolicy.DENY and len(parts) > 1:
            raise ValueError("Status code can only be specified with 'deny' policy")

        if policy == RateLimitPolicy.DENY and len(parts) > 1:
            try:
                status_code = int(parts[1])
                data["policy_status_code"] = status_code
            except ValueError as e:
                raise ValueError(
                    f"Invalid limit_policy format. Expected 'deny' or 'deny <status_code>', "
                    f"got '{limit_policy_input}'"
                ) from e

        data["limit_policy"] = policy

        return self


class DDoSProtectionProvider(Object):
    """DDoS protection interface provider implementation."""

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = DDOS_PROTECTION_RELATION_NAME,
    ) -> None:
        """Initialize the DDoSProtectionProvider.

        Args:
            charm: The charm that is instantiating the library.
            relation_name: The name of the relation.
        """
        super().__init__(charm, relation_name)

        self._relation_name = relation_name
        self.charm = charm

    def _update_relation_data(self) -> None:
        """Update the relation data with the current provider configuration."""
        relations = self.charm.model.relations.get(self._relation_name, [])
        for relation in relations:
          self._provider_data.dump(relation.data[self.charm.app], clear=True)
    def set_config(
        self,
        *,
        rate_limit_requests_per_minute: Optional[int] = None,
        rate_limit_connections_per_minute: Optional[int] = None,
        concurrent_connections_limit: Optional[int] = None,
        error_rate: Optional[int] = None,
        limit_policy: Optional[str] = None,
        ip_allow_list: Optional[list[str]] = None,
        http_request_timeout: Optional[int] = None,
        http_keepalive_timeout: Optional[int] = None,
        client_timeout: Optional[int] = None,
        deny_paths: Optional[list[str]] = None,
    ) -> None:
        """Update the DDoS protection configuration.

        Args:
            rate_limit_requests_per_minute: Maximum number of requests per minute per entry.
            rate_limit_connections_per_minute: Maximum number of connections per minute per entry.
            concurrent_connections_limit: Maximum number of concurrent connections per entry.
            error_rate: Number of errors per minute per entry to trigger the limit policy.
            limit_policy: Policy to be applied when limits are exceeded.
            ip_allow_list: List of IPv4 addresses or CIDR blocks to be allowed.
            http_request_timeout: Timeout for HTTP requests in seconds.
            http_keepalive_timeout: Timeout for HTTP keep-alive connections in seconds.
            client_timeout: Timeout for client connections in seconds.
            deny_paths: List of paths to deny.

        Raises:
            DataValidationError: When validation of the provided data fails.
        """
        try:
            self._provider_data = DDoSProtectionProviderAppData(
                rate_limit_requests_per_minute=rate_limit_requests_per_minute,
                rate_limit_connections_per_minute=rate_limit_connections_per_minute,
                concurrent_connections_limit=concurrent_connections_limit,
                error_rate=error_rate,
                limit_policy=cast(Optional[RateLimitPolicy], limit_policy),
                ip_allow_list=cast(Optional[list[IPv4Network | IPv4Address]], ip_allow_list),
                http_request_timeout=http_request_timeout,
                http_keepalive_timeout=http_keepalive_timeout,
                client_timeout=client_timeout,
                deny_paths=deny_paths,
            )
        except ValidationError as e:
            msg = f"Failed to validate DDoS protection configuration: {e}"
            logger.error(msg)
            raise DataValidationError(msg) from e

        # Only update relation data if at least one field is set
        if self._provider_data.model_dump(exclude_defaults=True):
            self._update_relation_data()


class DDoSProtectionRequirer(Object):
    """DDoS protection interface requirer implementation."""

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = DDOS_PROTECTION_RELATION_NAME,
    ) -> None:
        """Initialize the DDoSProtectionRequirer.

        Args:
            charm: The charm that is instantiating the library.
            relation_name: The name of the relation to bind to.
        """
        super().__init__(charm, relation_name)

        self._relation_name = relation_name
        self.charm = charm

    def get_ddos_config(self) -> Optional[DDoSProtectionProviderAppData]:
        """Retrieve the DDoS protection configuration from the provider.

        Returns:
            DDoSProtectionProviderAppData: The DDoS protection configuration if available,
                or None if the relation is not established or contains no data.

        Raises:
            DDoSProtectionInvalidRelationDataError: When data validation fails.
        """
        relations = self.charm.model.relations.get(self._relation_name, [])
        if not relations:
            return None

        relation = relations[0]
        if not relation.app:
            return None

        databag: MutableMapping[str, str] = relation.data.get(relation.app, {})
        if not databag:
            return None

        try:
            return cast(
                DDoSProtectionProviderAppData,
                DDoSProtectionProviderAppData.load(databag),
            )
        except DataValidationError as e:
            logger.error("Invalid DDoS protection configuration: %s", str(e))
            raise DDoSProtectionInvalidRelationDataError(
                f"Failed to load DDoS protection configuration: {e}"
            ) from e
