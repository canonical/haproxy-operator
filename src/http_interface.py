# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import typing

from ops import RelationChangedEvent
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, RelationDataContent, MutableMapping

from pydantic import BaseModel, Field, field_validator, ValidationError
import logging

logger = logging.getLogger()


class DataValidationError(Exception):
    """Raised when data validation fails when parsing relation data."""


class HTTPRequirerUnitData(BaseModel):
    hostname: str = Field(description="Hostname at which the unit is reachable.")
    port: int = Field(description="Port on which the unit is listening.")

    @field_validator("hostname", pre=True)
    @classmethod
    def validate_host(cls, hostname):  # noqa: N805  # pydantic wants 'cls' as first arg
        """Validate host."""
        assert isinstance(hostname, str), type(hostname)
        return hostname

    @field_validator("port", pre=True)
    @classmethod
    def validate_port(cls, port):  # noqa: N805  # pydantic wants 'cls' as first arg
        """Validate port."""
        assert isinstance(port, int), type(port)
        assert 0 < port < 65535, "port out of TCP range"
        return port

    @classmethod
    def from_relation_databag(cls, databag: MutableMapping):
        try:
            data = {
                k: json.loads(v)
                for k, v in databag.items()
                # Don't attempt to parse model-external values
                if k in {f.alias for f in cls.model_fields.values()}
            }
        except json.JSONDecodeError as exc:
            msg = f"invalid databag contents: expecting json. {databag}"
            logger.error(msg)
            raise DataValidationError(msg) from exc
        try:
            return cls.model_validate_json(json.dumps(data))  # type: ignore
        except ValidationError as exc:
            msg = f"failed to validate databag: {databag}"
            logger.debug(msg, exc_info=True)
            raise DataValidationError(msg) from exc


class HTTPRequirerData(BaseModel):
    unit_data = list[HTTPRequirerUnitData]


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

    __args__ = "hosts"
    hosts: typing.Sequence["HTTPRequirerData"] = ()


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

        units_data: list["HTTPRequirerUnitData"] = []
        for unit in relation.units:
            databag = _load_relation_data(relation.data[unit])

        self.on.data_provided.emit()


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
