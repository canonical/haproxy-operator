# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route-policy interface library.

This interface is used between the HAProxy charm (requirer) and the
haproxy-route-policy charm (provider).

The requirer publishes route policy requests under ``requests`` as a list of
HAProxy backend objects. The provider publishes approved entries under
``approved_backends`` and additionally exposes ``policy_backend_port`` and
provider unit addresses for policy web UI routing.
"""

import json
import logging
from typing import Annotated, MutableMapping, Optional, cast

from ops import CharmBase
from ops.charm import CharmEvents
from ops.framework import EventBase, EventSource, Object
from ops.model import Relation
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)
from validators import domain

# The unique Charmhub library identifier, never change it
LIBID = "24c99d77895e481d8661288f95884ee4"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2


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


class DataValidationError(Exception):
    """Raised when data validation fails."""


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
        # Custom config key: whether to nest the whole datastructure (as json)
        # under a field or spread it out at the toplevel.
        _NEST_UNDER=None,
    )  # type: ignore
    """Pydantic config."""

    @classmethod
    def load(cls, databag: MutableMapping) -> "_DatabagModel":
        """Load this model from a Juju json databag.

        Args:
            databag: Databag content.

        Raises:
            DataValidationError: When model validation failed.

        Returns:
            _DatabagModel: The validated model.
        """
        nest_under = cls.model_config.get("_NEST_UNDER")
        if nest_under:
            return cls.model_validate(json.loads(databag[nest_under]))

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
            logger.error(str(e), exc_info=True)
            raise DataValidationError(msg) from e

    def dump(
        self, databag: Optional[MutableMapping] = None, clear: bool = True
    ) -> Optional[MutableMapping]:
        """Write the contents of this model to Juju databag.

        Args:
            databag: The databag to write to.
            clear: Whether to clear the databag before writing.

        Returns:
            MutableMapping: The databag.
        """
        if clear and databag:
            databag.clear()

        if databag is None:
            databag = {}
        nest_under = self.model_config.get("_NEST_UNDER")
        if nest_under:
            databag[nest_under] = self.model_dump_json(
                by_alias=True,
                # skip keys whose values are default
                exclude_defaults=True,
            )
            return databag

        dct = self.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        databag.update({k: json.dumps(v) for k, v in dct.items()})
        return databag


class HaproxyRoutePolicyInvalidRelationDataError(Exception):
    """Raised when relation data validation for haproxy-route-policy fails."""


class HaproxyRoutePolicyBackendRequest(_DatabagModel):
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


class HaproxyRoutePolicyRequirerAppData(_DatabagModel):
    """Data model representing the requirer application data for haproxy-route-policy.

    Attributes:
        backend_requests: List of backend requests to be evaluated by the policy service.
    """

    backend_requests: list[HaproxyRoutePolicyBackendRequest] = Field(
        description="List of backends to be evaluated by the policy service."
    )

    @model_validator(mode="after")
    def validate_unique_backend_names(self):
        """Ensure that backend names are unique across all requests."""
        backend_names = [request.backend_name for request in self.backend_requests]
        if len(backend_names) != len(set(backend_names)):
            raise ValueError("Backend names must be unique across all requests.")
        return self


class HaproxyRoutePolicyProviderAppData(_DatabagModel):
    """haproxy-route-policy provider app databag schema."""

    approved_requests: list[HaproxyRoutePolicyBackendRequest] = Field(
        description="List of approved backend requests."
    )


class HaproxyRoutePolicyDataAvailableEvent(EventBase):
    """Emitted when requirer policy request data becomes available."""


class HaproxyRoutePolicyDataRemovedEvent(EventBase):
    """Emitted when one of the relations is removed."""


class HaproxyRoutePolicyProviderEvents(CharmEvents):
    """Events emitted by the policy provider helper."""

    data_available = EventSource(HaproxyRoutePolicyDataAvailableEvent)
    data_removed = EventSource(HaproxyRoutePolicyDataRemovedEvent)


class HaproxyRoutePolicyProvider(Object):
    """haproxy-route-policy provider implementation."""

    on = HaproxyRoutePolicyProviderEvents()  # pyright: ignore

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = HAPROXY_ROUTE_POLICY_RELATION_NAME,
    ) -> None:
        """Initialize provider helper.

        Args:
            charm: The charm instance using this helper.
            relation_name: Name of the relation endpoint.
            raise_on_validation_error: Raise on invalid remote data when True.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self._relation_name = relation_name
        on = self.charm.on
        self.framework.observe(on[self._relation_name].relation_changed, self._configure)
        self.framework.observe(on[self._relation_name].relation_created, self._configure)
        self.framework.observe(on[self._relation_name].relation_broken, self._on_data_removed)
        self.framework.observe(on[self._relation_name].relation_departed, self._on_data_removed)

    @property
    def relation(self) -> Relation | None:
        """Return the first relation for this endpoint, if any."""
        return self.charm.model.get_relation(self._relation_name)

    def _configure(self, _event: EventBase) -> None:
        """Handle relation lifecycle and emit data availability events."""
        if self.relation is not None:
            _ = self.get_data(self.relation)
            self.on.data_available.emit()

    def _on_data_removed(self, _event: EventBase) -> None:
        """Handle relation removal events."""
        self.on.data_removed.emit()

    def get_data(self, relation: Relation) -> HaproxyRoutePolicyRequirerAppData:
        """Fetch and validate requirer data.

        Args:
            relation: Relation to parse.

        Raises:
            HaproxyRoutePolicyInvalidRelationDataError: When validation fails and
                ``raise_on_validation_error`` is set.

        Returns:
            Parsed relation payloads and relation IDs that failed validation.
        """
        try:
            return cast(
                HaproxyRoutePolicyRequirerAppData,
                HaproxyRoutePolicyRequirerAppData.load(relation.data[relation.app]),
            )
        except DataValidationError as exc:
            logger.error(
                "haproxy-route-policy data validation failed for relation %s: %s",
                relation,
                str(exc),
            )
            raise HaproxyRoutePolicyInvalidRelationDataError(
                f"haproxy-route-policy data validation failed for relation: {relation}"
            ) from exc


class HaproxyRoutePolicyReadyEvent(EventBase):
    """Emitted when provider data is available to the requirer."""


class HaproxyRoutePolicyRemovedEvent(EventBase):
    """Emitted when the relation is removed from the requirer side."""


class HaproxyRoutePolicyRequirerEvents(CharmEvents):
    """Events emitted by the policy requirer helper."""

    ready = EventSource(HaproxyRoutePolicyReadyEvent)
    removed = EventSource(HaproxyRoutePolicyRemovedEvent)


class HaproxyRoutePolicyRequirer(Object):
    """haproxy-route-policy requirer implementation."""

    on = HaproxyRoutePolicyRequirerEvents()  # pyright: ignore

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
        self, backend_requests: list[HaproxyRoutePolicyBackendRequest]
    ) -> None:
        """Set and publish route policy requests."""
        relation = self.relation
        if not relation or not self.charm.unit.is_leader():
            return

        try:
            app_data = HaproxyRoutePolicyRequirerAppData(backend_requests=backend_requests)
        except ValidationError as exc:
            logger.error("Validation error when preparing requirer relation data.")
            raise DataValidationError(
                "Validation error when preparing requirer relation data."
            ) from exc

        app_data.dump(relation.data[self.charm.app], clear=True)
