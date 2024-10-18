# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import abc
import json
import logging

from ops import RelationBrokenEvent, RelationChangedEvent, RelationJoinedEvent
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, Relation, RelationDataContent

import legacy

logger = logging.getLogger()
SERVICES_CONFIGURATION_KEY = "services"
DEFAULT_HAPROXY_PORT = 80


class HTTPBackendAvailableEvent(RelationEvent):
    """Event representing that http data has been provided."""


class HTTPBackendRemovedEvent(RelationEvent):
    """Event representing that http data has been removed."""


class HTTPRequirerEvents(CharmEvents):
    """Container for HTTP Provider events.

    Attrs:
        http_backend_available: Custom event when integration data is provided.
        http_backend_removed: Custom event when integration data is removed.
    """

    http_backend_available = EventSource(HTTPBackendAvailableEvent)
    http_backend_removed = EventSource(HTTPBackendRemovedEvent)


class _IntegrationInterfaceBaseClass(Object):
    """Base class for integration interface classes.

    Attrs:
        relations: The list of Relation instances associated with the charm.
        bind_address: The unit address.
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

        observe(charm.on[relation_name].relation_joined, self._on_relation_joined)
        observe(charm.on[relation_name].relation_changed, self._on_relation_changed)
        observe(charm.on[relation_name].relation_broken, self._on_relation_broken)

    @abc.abstractmethod
    def _on_relation_joined(self, _: RelationJoinedEvent) -> None:
        """Abstract method to handle relation-joined event.

        Raises:
            NotImplementedError: if the abstract method is not implemented.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Abstract method to handle relation-changed event.

        Raises:
            NotImplementedError: if the abstract method is not implemented.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Abstract method to handle relation-changed event.

        Raises:
            NotImplementedError: if the abstract method is not implemented.
        """
        raise NotImplementedError

    @property
    def relations(self) -> list[Relation]:
        """The list of Relation instances associated with the charm."""
        return self.charm.model.relations.get(self.relation_name, [])

    @property
    def bind_address(self) -> str:
        """Get Unit bind address.

        Returns:
            The unit address, or an empty string if no address found.
        """
        if bind := self.model.get_binding("juju-info"):
            return str(bind.network.bind_address)
        return ""


class HTTPRequirer(_IntegrationInterfaceBaseClass):
    """HTTP interface provider class to be instantiated by the haproxy-operator charm.

    Attrs:
        on: Custom events that are used to notify the charm using the provider.
    """

    on = HTTPRequirerEvents()

    def _on_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event.
        """
        event.relation.data[self.charm.unit].update(
            {
                "public-address": self.bind_address,
            }
        )

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event.
        """
        self.on.http_backend_available.emit(
            event.relation,
            event.app,
            event.unit,
        )

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Handle relation-broken event.

        Args:
            event: relation-broken event.
        """
        self.on.http_backend_removed.emit(
            event.relation,
            event.app,
            event.unit,
        )

    def get_services(self) -> list:
        """Return the haproxy config for all services in the relation data.

        Returns:
            list: The list of haproxy config stanzas for all services in the relation data.
        """
        return legacy.generate_service_config(self.get_services_definition())

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


class HTTPProvider(_IntegrationInterfaceBaseClass):
    """HTTP interface provider class to be instantiated by the haproxy-operator charm."""

    def _on_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event.
        """
        event.relation.data[self.charm.unit].update(
            {"hostname": self.bind_address, "port": f"{DEFAULT_HAPROXY_PORT}"}
        )

    # We add a placeholder implementation of this method because of parent class
    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Handle relation-changed event."""
        logger.debug("Nothing to do for relation-changed hook of website relation, skipping.")

    def _on_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Handle relation-broken event.

        Args:
            event: relation-broken event.
        """
        event.relation.data[self.charm.unit].clear()


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
