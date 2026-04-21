# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route-policy interface library.

This interface is used between the HAProxy charm (requirer) and the
haproxy-route-policy charm (provider).

The requirer publishes route policy requests under ``backend_requests`` as a list of
HAProxy backend objects. The provider publishes approved entries under
``approved_requests`` and additionally exposes ``policy_backend_port`` and
provider unit addresses for policy web UI routing.
"""

import logging
from typing import Annotated

from ops import CharmBase
from ops.framework import Object
from ops.model import (
    Relation,
    RelationDataAccessError,
    RelationDataTypeError,
    RelationNotFoundError,
)
from pydantic import (
    BeforeValidator,
    Field,
    HttpUrl,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.dataclasses import dataclass
from validators import domain

# The unique Charmhub library identifier, never change it
LIBID = "24c99d77895e481d8661288f95884ee4"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 7


def valid_domain_with_wildcard(value: str) -> str:
    """Validate if value is a valid domain that can include a wildcard.

    The wildcard character (*) can't be at the TLD level, for example *.com is not valid.
    This is supported natively by the library ( e.g domain("com") will raise a ValidationError ).

    Raises:
        ValueError: When value is not a valid domain.

    Args:
        value: The value to validate.
    """
    fqdn = value[2:] if value.startswith("*.") else value
    if not bool(domain(fqdn)):
        raise ValueError(f"Invalid domain: {value}")
    return value


logger = logging.getLogger(__name__)
HAPROXY_ROUTE_POLICY_RELATION_NAME = "haproxy-route-policy"


class HaproxyRoutePolicyInvalidRelationDataError(Exception):
    """Raised when relation data validation for haproxy-route-policy fails."""


@dataclass
class HaproxyRoutePolicyBackendRequest:
    """Data model representing a single backend request from the requirer.

    Attributes:
        relation_id: The relation ID of the request.
        backend_name: The name of the HAProxy backend.
        hostname_acls: List of hostname ACLs for the backend.
        paths: List of paths for the backend.
        port: Port number for the backend.
    """

    relation_id: int = Field(description="Relation ID of the backend request.")
    backend_name: str = Field(description="Name of the HAProxy backend.")
    hostname_acls: list[Annotated[str, BeforeValidator(valid_domain_with_wildcard)]] = Field(
        description="List of hostname ACLs for the backend."
    )
    paths: list[str] = Field(description="List of paths for the backend.")
    port: int = Field(gt=0, le=65535, description="Port number for the backend.")


@dataclass
class HaproxyRoutePolicyRequirerAppData:
    """Data model representing the requirer application data for haproxy-route-policy.

    Attributes:
        backend_requests: List of backend requests to be evaluated by the policy service.
    """

    backend_requests: list[HaproxyRoutePolicyBackendRequest] = Field(
        description="List of backends to be evaluated by the policy service."
    )
    proxied_endpoint: str | None = Field(
        description=("URL for the proxied endpoint that's exposing the Django web UI."),
    )

    @field_validator("proxied_endpoint")
    def validate_proxied_endpoint(cls, value: str | None) -> str | None:
        """Validate that the proxied endpoint, if provided, is a valid URL."""
        if value is not None:
            try:
                TypeAdapter(HttpUrl).validate_python(value)
            except ValueError as exc:
                raise ValueError(f"Invalid proxied endpoint URL: {value}") from exc
        return value

    @model_validator(mode="after")
    def validate_unique_backend_names(self):
        """Ensure that backend names are unique across all requests."""
        backend_names = [request.backend_name for request in self.backend_requests]
        if len(backend_names) != len(set(backend_names)):
            raise ValueError("Backend names must be unique across all requests.")
        return self


@dataclass
class HaproxyRoutePolicyProviderAppData:
    """haproxy-route-policy provider app databag schema."""

    approved_requests: list[HaproxyRoutePolicyBackendRequest] = Field(
        description="List of approved backend requests."
    )
    policy_backend_port: int = Field(
        gt=0,
        le=65535,
        description="Port number for the policy backend service (e.g. for routing to policy web UI).",
    )
    model: str = Field(description="Model name where the policy backend is deployed.")


class HaproxyRoutePolicyProvider(Object):
    """haproxy-route-policy provider implementation."""

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = HAPROXY_ROUTE_POLICY_RELATION_NAME,
    ) -> None:
        """Initialize provider helper.

        Args:
            charm: The charm instance using this helper.
            relation_name: Name of the relation endpoint.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @property
    def relation(self) -> Relation | None:
        """Return the first relation for this endpoint, if any."""
        return self.charm.model.get_relation(self.relation_name)

    def set_approved_backend_requests(
        self, approved_requests: list[HaproxyRoutePolicyBackendRequest], policy_backend_port: int
    ) -> None:
        """Set and publish approved backend requests."""
        relation = self.relation
        if not relation or not self.charm.unit.is_leader():
            return

        try:
            app_data = HaproxyRoutePolicyProviderAppData(
                approved_requests=approved_requests,
                policy_backend_port=policy_backend_port,
                model=self.charm.model.name,
            )
            relation.save(app_data, self.charm.app)
        except (
            ValidationError,
            RelationDataTypeError,
            RelationDataAccessError,
            RelationNotFoundError,
        ) as exc:
            logger.error("Validation error when preparing provider relation data.")
            raise HaproxyRoutePolicyInvalidRelationDataError(
                "Validation error when preparing provider relation data."
            ) from exc


class HaproxyRoutePolicyRequirer(Object):
    """haproxy-route-policy requirer implementation."""

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = HAPROXY_ROUTE_POLICY_RELATION_NAME,
    ) -> None:
        """Initialize requirer helper.

        Args:
            charm: The charm instance using this helper.
            relation_name: Name of the relation endpoint.
            requests: Optional initial request backend list to publish.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self._relation_name = relation_name

    @property
    def relation(self) -> Relation | None:
        """Return the first relation for this endpoint, if any."""
        return self.charm.model.get_relation(self._relation_name)

    def provide_haproxy_route_policy_requests(
        self,
        backend_requests: list[HaproxyRoutePolicyBackendRequest],
        proxied_endpoint: str | None,
    ) -> None:
        """Set and publish route policy requests."""
        relation = self.relation
        if not relation or not self.charm.unit.is_leader():
            return

        try:
            app_data = HaproxyRoutePolicyRequirerAppData(
                backend_requests=backend_requests,
                proxied_endpoint=proxied_endpoint,
            )
            relation.save(app_data, self.charm.app)
        except (
            ValidationError,
            RelationDataTypeError,
            RelationDataAccessError,
            RelationNotFoundError,
        ) as exc:
            logger.error("Validation error when preparing requirer relation data.")
            raise HaproxyRoutePolicyInvalidRelationDataError(
                "Validation error when preparing requirer relation data."
            ) from exc
