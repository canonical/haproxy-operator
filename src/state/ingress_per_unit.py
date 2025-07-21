# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy ingress per unit charm state component."""

import dataclasses

from charms.traefik_k8s.v1.ingress_per_unit import (
    DataValidationError,
    IngressPerUnitProvider,
    RequirerData,
)

from .exception import CharmStateValidationBaseError

INGRESS_PER_UNIT_RELATION = "ingress_per_unit"


class IngressPerUnitIntegrationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when ingress_per_unit integration fails data validation."""


@dataclasses.dataclass(frozen=True)
class HAProxyBackend:
    """A component of charm state that represent an ingress per unit requirer.

    Attrs:
        backend_name: The name of the backend (computed).
        backend_path: The path prefix for the requirer unit.
        hostname_or_ip: The host or ip address of the requirer unit.
        port: The port that the requirer unit wishes to be exposed.
        strip_prefix: Whether to strip the prefix from the ingress url.
    """

    backend_name: str
    backend_path: str
    hostname_or_ip: str
    port: int
    strip_prefix: bool


@dataclasses.dataclass(frozen=True)
class IngressPerUnitRequirersInformation:
    """A component of charm state containing ingress per unit requirers information.

    Attrs:
        backends: The list of backends each corresponds to a requirer unit.
    """

    backends: list[HAProxyBackend]

    @classmethod
    def from_provider(
        cls, ingress_per_unit_provider: IngressPerUnitProvider
    ) -> "IngressPerUnitRequirersInformation":
        """Get requirer information from an IngressPerUnitProvider instance.

        Args:
            ingress_per_unit_provider: The ingress per unit provider library.

        Raises:
            IngressPerUnitIntegrationDataValidationError: When data validation failed.

        Returns:
            IngressPerUnitRequirersInformation: Information about ingress requirers.
        """
        backends = []
        for integration in ingress_per_unit_provider.relations:
            for unit in integration.units:
                try:
                    integration_data: RequirerData = ingress_per_unit_provider.get_data(
                        integration, unit
                    )
                    unit_name = "_".join(integration_data["name"].split("/"))
                    backend_name = f"{integration_data['model']}_{unit_name}"
                    backend_path = f"{integration_data['model']}-{integration_data['name']}"
                    backends.append(
                        HAProxyBackend(
                            backend_name=backend_name,
                            backend_path=backend_path,
                            hostname_or_ip=integration_data["host"],
                            port=integration_data["port"],
                            strip_prefix=integration_data["strip-prefix"],
                        )
                    )
                except DataValidationError as exc:
                    raise IngressPerUnitIntegrationDataValidationError(
                        "Validation of ingress per unit relation data failed."
                    ) from exc
        return cls(backends=backends)
