# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import logging
import typing

from ops import RelationChangedEvent
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, Relation, RelationDataContent
from pydantic import BaseModel, Field, ValidationError, field_validator

from state.validation import validate_config_and_integration

logger = logging.getLogger()


class DataValidationError(Exception):
    """Raised when data validation fails when parsing relation data."""


class HTTPRequirerUnitData(BaseModel):
    """_summary_

    Attrs:
        hostname: _description_
        port: _description_
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


class _IPAEvent(RelationEvent):
    __args__: tuple[str, ...] = ()
    __optional_kwargs__: dict[str, any] = {}

    @classmethod
    def __attrs__(cls):
        return cls.__args__ + tuple(cls.__optional_kwargs__.keys())

    def __init__(self, handle, relation, *args, **kwargs):
        super().__init__(handle, relation)

        if not len(self.__args__) == len(args):
            raise TypeError("expected {} args, got {}".format(len(self.__args__), len(args)))

        for attr, obj in zip(self.__args__, args):
            setattr(self, attr, obj)
        for attr, default in self.__optional_kwargs__.items():
            obj = kwargs.get(attr, default)
            setattr(self, attr, obj)

    def snapshot(self):
        dct = super().snapshot()
        for attr in self.__attrs__():
            obj = getattr(self, attr)
            try:
                dct[attr] = obj
            except ValueError as e:
                raise ValueError(
                    "cannot automagically serialize {}: "
                    "override this method and do it "
                    "manually.".format(obj)
                ) from e

        return dct

    def restore(self, snapshot) -> None:
        super().restore(snapshot)
        for attr, obj in snapshot.items():
            setattr(self, attr, obj)


class HTTPDataProvidedEvent(_IPAEvent):
    """Event representing that http data has been provided."""

    __args__ = ("hosts",)
    hosts: typing.Sequence["HTTPRequirerUnitData"] = ()


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

    on = HTTPProviderEvents()

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
    ):
        """Initialize the interface provider class.

        Args:
            charm: The charm implementing the requirer or provider.
            integration_name: Name of the integration using the interface.
        """
        super().__init__(charm, relation_name)
        self.integration = self.model.get_relation(self.integration_name)

    @validate_config_and_integration(defer=False)
    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handle relation-changed event.

        Args:
            event: relation-changed event
        """
        integration = event.relation
        self.on.data_provided.emit(
            integration,
            [unit.model_dump() for unit in self.get_integration_unit_data(integration)],
        )

    def get_integration_unit_data(self, integration: Relation):
        """_summary_

        Args:
            integration (Relation): _description_
        """

        return [
            HTTPRequirerUnitData.from_dict(_load_relation_data(integration.data[unit]))
            for unit in integration.units
        ]


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
