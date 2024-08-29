# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy http interface module."""

import json
import logging
import typing
import yaml
from typing_extensions import Self
from ops import RelationBrokenEvent, RelationChangedEvent
from ops.charm import CharmBase, CharmEvents, RelationEvent
from ops.framework import EventSource, Object
from ops.model import ModelError, Relation, RelationDataContent, Unit, Application
from pydantic import BaseModel, ValidationError, model_validator, IPvAnyAddress
from dataclasses import dataclass

logger = logging.getLogger()
SERVICES_CONFIGURATION_KEY = "services"


class DataValidationError(Exception):
    """Raised when data validation fails when parsing relation data."""


class HTTPServiceDefinition(BaseModel):
    service_name: str
    service_host: IPvAnyAddress
    service_port: int
    service_options: typing.Optional[list[str]]
    server_options: typing.Optional[list[str]]
    servers: typing.Optional[list[list[str]]]

    @classmethod
    def from_dict(cls, data: dict) -> "HTTPServiceDefinition":
        """Parse integration databag into data class.

        Args:
            data: Integration databag.

        Raises:
            DataValidationError: When data validation failed.

        Returns:
            HTTPServiceDefinition: Instance of the parsed requirer unit data class.
        """
        try:
            return cls.model_validate_json(json.dumps(data))
        except ValidationError as exc:
            msg = f"failed to validate databag: {data}"
            logger.error(msg, exc_info=True)
            raise DataValidationError(msg) from exc

    def __eq__(self, target: "HTTPServiceDefinition") -> bool:
        return (
            self.service_host == target.service_host
            and self.port == target.service_port
            and self.service_options == target.service_options
        )


class HTTPRequirerUnitData(BaseModel):
    """HTTP interface requirer unit data.

    Attrs:
        hostname: Hostname at which the unit is reachable.
        port: Port on which the unit is listening.
    """

    hostname: typing.Optional[str]
    port: typing.Optional[int]
    services: typing.Optional[list[HTTPServiceDefinition]]

    @model_validator(mode="after")
    def validate_unit_data(self) -> Self:
        if self.services is not None:
            assert self.hostname is None and self.port is None
            return Self

        assert isinstance(self.hostname, str), type(self.hostname)
        assert isinstance(self.port, int), type(self.port)
        assert 0 < self.port < 65535, "port out of TCP range"
        return Self

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
            if services_definition_data := data.get(SERVICES_CONFIGURATION_KEY):
                services = []
                for service in services_definition_data:
                    # Parse service_options if it's a string
                    if service_options := service.get("service_options") and isinstance(
                        service_options, str
                    ):
                        service["service_options"] = list(
                            filter(None, (v.strip() for v in service_options.split(",")))
                        )
                    # Parse server_options if it's a string
                    if server_options := service.get("server_options") and isinstance(
                        server_options, str
                    ):
                        service["server_options"] = list(
                            filter(None, (v.strip() for v in server_options.split(",")))
                        )
                    services.append(service)

            return cls.model_validate_json(json.dumps(data))
        except ValidationError as exc:
            msg = f"failed to validate databag: {data}"
            logger.error(msg, exc_info=True)
            raise DataValidationError(msg) from exc


@dataclass(frozen=True)
class HTTPRequierApplicationData:
    """HTTP interface requirer unit data.

    Attrs:
        hostname: Hostname at which the unit is reachable.
        port: Port on which the unit is listening.
    """

    single_service_configuration: typing.Optional[dict[Unit, HTTPRequirerUnitData]]
    relation_driven_configuration: typing.Optional[dict[str, list[HTTPServiceDefinition]]]
    default_service: typing.Optional[str]

    @classmethod
    def from_requirer_unit_data(
        cls, units_data: dict[Unit, HTTPRequirerUnitData], application: str
    ) -> "HTTPRequierApplicationData":
        if services_units_data := [unit.services for unit in units_data.values()]:
            # `services` is configured, we're under relation_driven_proxying
            if None in services_units_data:
                logger.error(
                    "Service configuration not consistent between units: %r", services_units_data
                )
                raise DataValidationError("Service configuration not consistent between units.")

            relation_driven_configuration: dict[str, HTTPServiceDefinition] = {}
            default_service = None
            for unit_data in services_units_data:
                service_key = f"{application}-{service.service_name}"
                for service in unit_data:
                    if not relation_driven_configuration:
                        default_service = service_key

                    if existing := relation_driven_configuration.get(service_key):
                        if existing != service:
                            raise DataValidationError(
                                "Services configuration not consistent between app units."
                            )

                        existing.servers.extend(service.servers)
                        continue

                    relation_driven_configuration[service_key] = service

            return cls(
                single_service_configuration=None,
                relation_driven_configuration=relation_driven_configuration,
                default_service=default_service,
            )

        # `services` is not configured, we're under single_service_proxying
        if any(
            unit.hostname is not None and unit.port is not None for unit in units_data.values()
        ):
            logger.error("hostname/port configuration is missing on some units: %r", units_data)
            raise DataValidationError("hostname/port configuration is missing on some units.")

        return cls(
            single_service_configuration=units_data,
            relation_driven_configuration=None,
            default_service=None,
        )


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
        integrations: The list of Relation instances associated with the charm.
    """

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
    def integrations(self) -> list[Relation]:
        """The list of Relation instances associated with the charm."""
        return list(self.charm.model.relations[self.integration_name])


class HTTPProvider(_IntegrationInterfaceBaseClass):
    """HTTP interface provider class to be instantiated by the haproxy-operator charm.

    Attrs:
        on: Custom events that are used to notify the charm using the provider.
    """

    on = HTTPProviderEvents()  # type: ignore

    def is_integration_ready(self, integration: Relation) -> bool:
        """Check if integration is ready.

        Args:
            integration: Relation instance.

        Returns:
            False: If data validation failed on integration unit data.
        """
        try:
            self.get_requirer_application_data(integration)
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

    def get_requirer_application_data(self, integration: Relation) -> HTTPRequierApplicationData:
        """Parse and validate the integration units databag.

        Args:
            integration: Relation instance.

        Returns:
            dict: Parsed relation data for each unit.
        """
        return HTTPRequierApplicationData.from_requirer_unit_data(
            {
                unit: HTTPRequirerUnitData.from_dict(_load_relation_data(integration.data[unit]))
                for unit in integration.units
            },
            integration.app.name,
        )


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
            if key == SERVICES_CONFIGURATION_KEY:
                continue
            try:
                relation_data[key] = json.loads(relation_data_content[key])
            except (json.decoder.JSONDecodeError, TypeError):
                relation_data[key] = relation_data_content[key]
    except ModelError:
        pass

    if services_config_data := relation_data_content.get(SERVICES_CONFIGURATION_KEY):
        if services_config_yaml := yaml.safe_load(services_config_data):
            relation_data[SERVICES_CONFIGURATION_KEY] = services_config_yaml

    return relation_data
