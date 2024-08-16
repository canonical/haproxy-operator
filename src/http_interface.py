# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import typing

from ops import RelationChangedEvent
from ops.charm import CharmBase, CharmEvents
from ops.framework import EventBase, EventSource, Handle, Object
from ops.model import ModelError, RelationDataContent


class HTTPDataProvidedEvent(EventBase):
    """Event representing that http data has been provided."""

    def __init__(self, handle: Handle, hostname: str, port: int):
        """Initialize the data-provided event.

        Args:
            handle: Used by parent class
            hostname: Requirer-provided hostname.
            port: Requirer-provided port.
        """
        super().__init__(handle)
        self.hostname = hostname
        self.port = port

    def snapshot(self) -> dict:
        """Return snapshot.

        Returns: The snapshot to return.
        """
        return {"hostname": self.hostname, "port": self.port}

    def restore(self, snapshot: dict) -> None:
        """Restore snapshot.

        Args:
            snapshot: The snapshot to restore
        """
        self.hostname = typing.cast(str, snapshot.get("hostname"))
        self.port = typing.cast(int, snapshot.get("port"))


class HTTPProviderEvents(CharmEvents):
    """Container for HTTP Provider events.

    Attrs:
        data_provided: Custom event when integration data is provided.
    """

    data_provided = EventSource(HTTPDataProvidedEvent)


class _IntegrationInterfaceBaseClass(Object):
    """Base class for integration interface classes."""

    def __init__(self, charm: CharmBase, integration_name: str):
        """Initialize the interface base class.

        Args:
            charm: The charm implementing the requirer or provider.
            integration_name: Name of the integration using the interface.
        """
        super().__init__(charm, integration_name)

        self.charm: CharmBase = charm
        self.integration_name = integration_name
        self.framework.observe(
            charm.on[integration_name].relation_changed, self._on_relation_changed
        )

    def _on_relation_changed(self, _: RelationChangedEvent) -> None:
        """Abstract method to handle relation-changed event."""


class HTTPProvider(_IntegrationInterfaceBaseClass):
    """HTTP interface provider class to be instantiated by the haproxy-operator charm.

    Attrs:
        on: Custom events that are used to notify the charm using the provider.
    """

    on = HTTPProviderEvents()  # type: ignore

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event
        """
        relation = event.relation
        for unit in relation.units:
            databag = _load_relation_data(relation.data[unit])
            self.on.data_provided.emit(
                relation, databag.get("hostname"), typing.cast(int, databag.get("port"))
            )


def _load_relation_data(relation_data_content: RelationDataContent) -> dict:
    """Load relation data from the relation data bag.

    Json loads all data.

    Args:
        relation_data_content: Relation data from the databag

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
