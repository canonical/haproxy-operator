# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import logging

from ops import RelationBrokenEvent, RelationChangedEvent, RelationJoinedEvent
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, Relation, RelationDataContent

import legacy

logger = logging.getLogger()
SERVICES_CONFIGURATION_KEY = "services"


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
        observe(charm.on[relation_name].relation_joined, self._on_relation_joined)
        observe(charm.on[relation_name].relation_changed, self._on_relation_changed)
        observe(charm.on[relation_name].relation_departed, self._on_relation_changed)
        observe(charm.on[relation_name].relation_broken, self._on_relation_broken)

    def _on_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Abstract method to handle relation-joined event."""

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

    def _on_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event.
        """
        event.relation.data[self.charm.unit].update(
            {
                "public-address": self.charm.bind_address,  # type: ignore
            }
        )

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

    def get_services_definition(self) -> dict:
        """Augment services_dict with service definitions from relation data.

        Returns:
            A dictionary containing the definition of all services.
        """
        relation_data = [
            (unit, _load_relation_data(relation.data[unit]))
            for relation in self.relations
            for unit in relation.units
        ]
        return legacy.get_services_from_relation_data(relation_data)


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
