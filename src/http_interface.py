# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import logging
import typing
import yaml
from typing_extensions import Self
from ops import RelationBrokenEvent, RelationChangedEvent, RelationData
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, Relation, RelationDataContent
from pydantic import BaseModel, ValidationError, model_validator
from operator import itemgetter
import legacy

logger = logging.getLogger()
SERVICES_CONFIGURATION_KEY = "services"


class DataValidationError(Exception):
    """Raised when data validation fails when parsing relation data."""


class HTTPRequirerUnitData(BaseModel):
    """HTTP interface requirer unit data.

    Attrs:
        hostname: Hostname at which the unit is reachable.
        port: Port on which the unit is listening.
    """

    hostname: typing.Optional[str] = None
    port: typing.Optional[int] = None

    @model_validator(mode="after")
    def validate_unit_data(self) -> Self:
        """_summary_

        Returns:
            Self: _description_
        """
        assert isinstance(self.hostname, str), type(self.hostname)
        assert isinstance(self.port, int), type(self.port)
        assert 0 < self.port < 65535, "port out of TCP range"
        return self

    @classmethod
    def from_dict(cls, data: dict) -> "HTTPRequirerUnitData":
        """Parse integration databag into data class.

        Args:
            data: Integration databag.

        Raises:
            DataValidationError: When data validation failed.

        Returns:
            HTTPRequirerUnitData: Instance of the parsed requirer unit data class.
        """
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
        data_removed: Custom event when integration data is removed.
    """

    data_provided = EventSource(HTTPDataProvidedEvent)
    data_removed = EventSource(HTTPDataRemovedEvent)


class _IntegrationInterfaceBaseClass(Object):
    """Base class for integration interface classes.

    Attrs:
        relations: The list of Relation instances associated with the charm.
    """

    def __init__(self, charm: CharmBase, relation_name: str):
        """Initialize the interface base class.

        Args:
            charm: The charm implementing the requirer or provider.
            relation_name: Name of the integration using the interface.
        """
        super().__init__(charm, relation_name)

        observe = self.framework.observe
        self.charm: CharmBase = charm
        self.relation_name = relation_name

        observe(charm.on[relation_name].relation_created, self._on_relation_changed)
        observe(charm.on[relation_name].relation_joined, self._on_relation_changed)
        observe(charm.on[relation_name].relation_changed, self._on_relation_changed)
        observe(charm.on[relation_name].relation_departed, self._on_relation_changed)
        observe(charm.on[relation_name].relation_broken, self._on_relation_broken)

    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Abstract method to handle relation-changed event."""

    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Abstract method to handle relation-changed event."""

    @property
    def relations(self) -> list[Relation]:
        """The list of Relation instances associated with the charm."""
        return list(self.charm.model.relations[self.relation_name])


class HTTPProvider(_IntegrationInterfaceBaseClass):
    """HTTP interface provider class to be instantiated by the haproxy-operator charm.

    Attrs:
        on: Custom events that are used to notify the charm using the provider.
    """

    on = HTTPProviderEvents()  # type: ignore

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event.
        """

        self.on.data_provided.emit(
            event.relation,
            event.app,
            event.unit,
        )

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Handle relation-broken event.

        Args:
            event: relation-broken event.
        """
        self.on.data_removed.emit(
            event.relation,
            event.app,
            event.unit,
        )

    def get_services_definition(self):
        # Augment services_dict with service definitions from relation data.
        relation_data = [
            (unit, _load_relation_data(relation.data[unit]))
            for relation in self.relations
            for unit in relation.units
        ]
        return legacy.get_services_from_relation_data(relation_data)

    def get_unit_hostname_port(self, relation: RelationData):
        return


def _load_relation_data(relation_data_content: RelationDataContent) -> dict:
    """Load relation data from the relation data bag.

    Json loads all data and yaml loads the services definition.
    Does not do data validation.

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
