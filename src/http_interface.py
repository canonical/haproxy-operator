# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import logging

from ops import RelationBrokenEvent, RelationChangedEvent
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, Relation, RelationDataContent
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger()


class DataValidationError(Exception):
    """Raised when data validation fails when parsing relation data."""


class HTTPRequirerUnitData(BaseModel):
    """HTTP interface requirer unit data.

    Attrs:
        hostname: Hostname at which the unit is reachable.
        port: Port on which the unit is listening.
    """

    hostname: str = Field(alias="hostname", description="Hostname at which the unit is reachable.")
    port: int = Field(alias="port", description="Port on which the unit is listening.")

    @field_validator("hostname")
    @classmethod
    def validate_host(cls, hostname):
        """Validate host."""
        assert isinstance(hostname, str), type(hostname)
        return hostname

    @field_validator("port")
    @classmethod
    def validate_port(cls, port):
        """Validate port."""
        assert isinstance(port, int), type(port)
        assert 0 < port < 65535, "port out of TCP range"
        return port

    @classmethod
    def from_dict(cls, data: dict):
        try:
            return cls.model_validate_json(json.dumps(data))
        except ValidationError as exc:
            msg = f"failed to validate databag: {data}"
            logger.error(msg, exc_info=True)
            raise DataValidationError(msg) from exc


class HTTPDataProvidedEvent(RelationEvent):
    """Event representing that http data has been provided."""


class HTTPDataRemovedEvent(RelationEvent):
    """Event representing that http data has been removed."""


class HTTPProviderEvents(CharmEvents):
    """Container for HTTP Provider events.

    Attrs:
        data_provided: Custom event when integration data is provided.
        data_provided: Custom event when integration data is removed.
    """

    data_provided = EventSource(HTTPDataProvidedEvent)
    data_removed = EventSource(HTTPDataRemovedEvent)


class _IntegrationInterfaceBaseClass(Object):
    """Base class for integration interface classes."""

    def __init__(self, charm: CharmBase, integration_name: str):
        """Initialize the interface base class.

        Args:
            charm: The charm implementing the requirer or provider.
            integration_name: Name of the integration using the interface.
        """
        super().__init__(charm, integration_name)

        observe = self.framework.observe
        self.charm: CharmBase = charm
        self.integration_name = integration_name

        observe(charm.on[integration_name].relation_created, self._on_relation_changed)
        observe(charm.on[integration_name].relation_joined, self._on_relation_changed)
        observe(charm.on[integration_name].relation_changed, self._on_relation_changed)
        observe(charm.on[integration_name].relation_departed, self._on_relation_changed)
        observe(charm.on[integration_name].relation_broken, self._on_relation_broken)

    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Abstract method to handle relation-changed event."""

    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Abstract method to handle relation-changed event."""

    @property
    def integrations(self):
        """The list of Relation instances associated with the charm."""
        return list(self.charm.model.relations[self.integration_name])


class HTTPProvider(_IntegrationInterfaceBaseClass):
    """HTTP interface provider class to be instantiated by the haproxy-operator charm.

    Attrs:
        on: Custom events that are used to notify the charm using the provider.
    """

    on = HTTPProviderEvents()

    def __init__(
        self,
        charm: CharmBase,
        integration_name: str,
    ):
        """Initialize the interface provider class.

        Args:
            charm: The charm implementing the requirer or provider.
            integration_name: Name of the integration using the interface.
        """
        super().__init__(charm, integration_name)

    def is_integration_ready(self, integration: Relation) -> bool:
        """Check if integration is ready.

        Args:
            integration: Relation instance.

        Returns:
            False: If data validation failed on integration unit data.
        """
        try:
            self.get_integration_unit_data(integration)
        except DataValidationError:
            logger.exception("Data validation failed for unit data.")
            return False
        return True

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event.
        """
        if not self.is_integration_ready(event.relation):
            return

        self.on.data_provided.emit(
            event.relation,
            event.app,
            event.unit,
        )

    def _on_relation_broken(self, event):
        """Handle relation-broken event.

        Args:
            event: relation-broken event.
        """
        self.on.data_removed.emit(
            event.relation,
            event.app,
            event.unit,
        )

    def get_integration_unit_data(self, integration: Relation):
        """Parse and validate the integration units databag.

        Args:
            integration: Relation instance.
        """
        return {
            unit: HTTPRequirerUnitData.from_dict(_load_relation_data(integration.data[unit]))
            for unit in integration.units
        }


def _load_relation_data(relation_data_content: RelationDataContent) -> dict:
    """Load relation data from the relation data bag.

    Json loads all data.

    Args:
        relation_data_content: Relation data from the databag.

    Returns:
        dict: Relation data in dict format.
    """
    relation_data = {}
    try:
        for key in relation_data_content:
            try:
                relation_data[key] = json.loads(relation_data_content[key])
            except (json.decoder.JSONDecodeError, TypeError):
                relation_data[key] = relation_data_content[key]
    except ModelError:
        pass
    return relation_data
