# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy ingress charm state component."""

import dataclasses

from charms.traefik_k8s.v2.ingress import DataValidationError, IngressPerAppProvider

from .exception import CharmStateValidationBaseError

INGRESS_RELATION = "ingress"


class IngressIntegrationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


@dataclasses.dataclass(frozen=True)
class HAProxyServer:
    """A component of charm state that represent an ingress requirer unit.

    Attrs:
        server_name: The name of the unit with invalid characters replaced.
        hostname_or_ip: The host or ip address of the requirer unit.
        port: The port that the requirer application wishes to be exposed.
    """

    server_name: str
    hostname_or_ip: str
    port: int


@dataclasses.dataclass(frozen=True)
class HAProxyBackend:
    """A component of charm state that represent an ingress requirer application.

    Attrs:
        backend_name: The name of the backend (computed).
        servers: The list of server each corresponding to a requirer unit.
        strip_prefix: Whether to strip the prefix from the ingress url.
    """

    backend_name: str
    servers: list[HAProxyServer]
    strip_prefix: bool = False


@dataclasses.dataclass(frozen=True)
class IngressRequirersInformation:
    """A component of charm state containing ingress requirers information.

    Attrs:
        backends: The list of backends each corresponds to a requirer application.
    """

    backends: list[HAProxyBackend]

    @classmethod
    def from_provider(
        cls, ingress_provider: IngressPerAppProvider
    ) -> "IngressRequirersInformation":
        """Get TLS information from a charm instance.

        Args:
            ingress_provider: The ingress provider library.

        Raises:
            IngressIntegrationDataValidationError: When data validation failed.

        Returns:
            IngressRequirersInformation: Information about ingress requirers.
        """
        backends = []
        for integration in ingress_provider.relations:
            try:
                integration_data = ingress_provider.get_data(integration)
                strip_prefix = bool(integration_data.app.strip_prefix)
                backend_name = f"{integration_data.app.model}-{integration_data.app.name}"
                servers = []
                for i, unit_data in enumerate(integration_data.units):
                    hostname_or_ip = unit_data.ip if unit_data.ip else unit_data.host
                    port = integration_data.app.port
                    servers.append(
                        HAProxyServer(
                            hostname_or_ip=hostname_or_ip,
                            port=port,
                            server_name=f"{backend_name}-{i}",
                        )
                    )
                backends.append(
                    HAProxyBackend(
                        backend_name=backend_name, servers=servers, strip_prefix=strip_prefix
                    )
                )
            except DataValidationError as exc:
                raise IngressIntegrationDataValidationError(
                    "Validation of ingress relation data failed."
                ) from exc
        return cls(backends=backends)
