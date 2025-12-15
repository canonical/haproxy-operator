# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy route charm state component."""

import logging
from functools import cached_property
from typing import Optional, cast

from charms.haproxy.v0.haproxy_route_tcp import (
    HaproxyRouteTcpProvider,
    HaproxyRouteTcpRequirersData,
)
from charms.haproxy.v1.haproxy_route import (
    DataValidationError,
    HaproxyRewriteMethod,
    HaproxyRouteProvider,
    HaproxyRouteRequirerData,
    LoadBalancingAlgorithm,
    RequirerApplicationData,
    ServerHealthCheck,
)
from pydantic import Field, IPvAnyAddress, model_validator
from pydantic.dataclasses import dataclass
from typing_extensions import Self

from .exception import CharmStateValidationBaseError
from .haproxy_route_tcp import HAProxyRouteTcpEndpoint

HAPROXY_ROUTE_RELATION = "haproxy-route"
HAPROXY_PEER_INTEGRATION = "haproxy-peers"
logger = logging.getLogger()


class HaproxyRouteIntegrationDataValidationError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


@dataclass(frozen=True)
class HAProxyRouteServer:
    """A representation of a server in the backend section of the haproxy config.

    Attrs:
        server_name: The name of the unit with invalid characters replaced.
        address: The IP address of the requirer unit.
        port: The port that the requirer application wishes to be exposed.
        protocol: The protocol that the backend service speaks. "http" (default) or "https".
        check: Health check configuration.
        maxconn: Maximum allowed connections before requests are queued.
        external_grpc_port: Optional external gRPC port.
    """

    server_name: str
    address: IPvAnyAddress
    port: int
    protocol: str
    check: Optional[ServerHealthCheck]
    maxconn: Optional[int]
    external_grpc_port: Optional[int]


@dataclass(frozen=True)
class HAProxyRouteBackend:
    """A component of charm state that represent an ingress requirer application.

    Attrs:
        relation_id: The id of the relation, used to publish the proxied endpoints.
        application_data: requirer application data.
        backend_name: The name of the backend (computed).
        servers: The list of server each corresponding to a requirer unit.
        external_hostname: Configured haproxy hostname.
        hostname_acls: The list of hostname ACLs.
        load_balancing_configuration: Load balancing configuration for the haproxy backend.
        rewrite_configurations: Rewrite configuration.
        path_acl_required: Indicate if path routing is required.
        deny_path_acl_required: Indicate if deny_path is required.
        consistent_hashing: Use consistent hashing to avoid redirection
            when servers are added/removed.
    """

    relation_id: int
    application_data: RequirerApplicationData
    servers: list[HAProxyRouteServer]
    external_hostname: Optional[str]

    @property
    def backend_name(self) -> str:
        """The backend name.

        Returns:
            str: The backend name.
        """
        return self.application_data.service

    @property
    def path_acl_required(self) -> bool:
        """Indicate if path routing is required.

        Returns:
            bool: Whether the `paths` attribute in the requirer data is empty.
        """
        return bool(self.application_data.paths)

    @property
    def deny_path_acl_required(self) -> bool:
        """Indicate if deny_path is required.

        Returns:
            bool: Whether the `deny_paths` attribute in the requirer data is empty.
        """
        return bool(self.application_data.deny_paths)

    @cached_property
    def hostname_acls(self) -> list[str]:
        """Build the list of hostname ACL for the backend.

        Combines the hostname and additional_hostnames attribute into a list of hostname ACLs.
        Returns the configured external-hostname if hostname is not set.
        Returns an empty list if both external-hostname and the hostname attribute are not set.

        Returns:
            list[str]: List of hostname for ACL matching.
        """
        if not self.application_data.hostname:
            if not self.external_hostname:
                return []

            return [self.external_hostname]

        return [self.application_data.hostname, *self.application_data.additional_hostnames]

    # We disable no-member here because pylint doesn't know that
    # self.application_data.load_balancing Has a default value set
    # pylint: disable=no-member
    @property
    def load_balancing_configuration(self) -> str:
        """Build the load balancing configuration for the haproxy backend.

        Returns:
            str: The haproxy load balancing configuration for the backend.
        """
        if self.application_data.load_balancing.algorithm == LoadBalancingAlgorithm.COOKIE:
            # The library ensures that if algorithm == cookie
            # then the cookie attribute must be not none
            return f"hash req.cook({cast(str, self.application_data.load_balancing.cookie)})"
        return str(self.application_data.load_balancing.algorithm.value)

    @property
    def consistent_hashing(self) -> bool:
        """Indicate if consistent hashing should be applied for this backend.

        Returns:
            bool: Whether consistent hashing should be applied.
        """
        return (
            self.application_data.load_balancing.consistent_hashing
            and self.application_data.load_balancing.algorithm
            in [LoadBalancingAlgorithm.COOKIE, LoadBalancingAlgorithm.SRCIP]
        )

    @property
    def rewrite_configurations(self) -> list[str]:
        """Build the rewrite configurations.

        For example, method = SET_HEADER, header = COOKIE, expression = "testing"
        will result in the following rewrite config:

        http-request set-header COOKIE testing

        Returns:
            list[str]: The rewrite configurations.
        """
        rewrite_configurations: list[str] = []
        for rewrite in self.application_data.rewrites:
            if rewrite.method == HaproxyRewriteMethod.SET_HEADER:
                rewrite_configurations.append(
                    f"{rewrite.method.value!s} {rewrite.header} {rewrite.expression}"
                )
                continue
            rewrite_configurations.append(f"{rewrite.method.value!s} {rewrite.expression}")
        return rewrite_configurations

    @property
    def external_grpc_port(self) -> int | None:
        """Get the external grpc port if grpc is used.

        Returns:
            int | None: The external grpc port.
        """
        return self.application_data.external_grpc_port


# pylint: disable=too-many-locals
@dataclass(frozen=True)
class HaproxyRouteRequirersInformation:
    """A component of charm state containing haproxy-route requirers information.

    Attrs:
        backends: The list of backends each corresponds to a requirer application.
        stick_table_entries: List of stick table entries in the haproxy "peer" section.
        peers: List of IP address of haproxy peer units.
        relation_ids_with_invalid_data: List of haproxy-route relation ids
            that contains invalid data.
        relation_ids_with_invalid_data_tcp: List of haproxy-route-tcp relation ids
            that contains invalid data.
        tcp_endpoints: List of frontend/backend pairs in TCP mode.
    """

    backends: list[HAProxyRouteBackend]
    stick_table_entries: list[str]
    peers: list[IPvAnyAddress]
    relation_ids_with_invalid_data: list[int]
    relation_ids_with_invalid_data_tcp: list[int]
    tcp_endpoints: list[HAProxyRouteTcpEndpoint] = Field(strict=False)

    @classmethod
    def from_provider(  # pylint: disable=too-many-arguments
        cls,
        *,
        haproxy_route: HaproxyRouteProvider,
        haproxy_route_tcp: HaproxyRouteTcpProvider,
        external_hostname: Optional[str],
        peers: list[str],
        ca_certs_configured: bool,
    ) -> "HaproxyRouteRequirersInformation":
        """Initialize the HaproxyRouteRequirersInformation state component.

        Args:
            haproxy_route: The haproxy-route provider class.
            haproxy_route_tcp: The haproxy-route-tcp provider class.
            external_hostname: The charm's configured hostname.
            peers: List of IP address of haproxy peer units.
            ca_certs_configured: If ca certificates are configured for haproxy backends.

        Raises:
            HaproxyRouteIntegrationDataValidationError: When data validation failed.

        Returns:
            HaproxyRouteRequirersInformation: Information about requirers
                for the haproxy-route interface.
        """
        try:
            # This is used to check that requirers don't ask for the same backend name.
            backend_names: set[str] = set()
            # Control stick tables for rate_limiting and
            # eventually any shared values between haproxy units.
            stick_table_entries: list[str] = []
            requirers = haproxy_route.get_data(haproxy_route.relations)
            backends: list[HAProxyRouteBackend] = []
            relation_ids_with_invalid_data = requirers.relation_ids_with_invalid_data
            for requirer in requirers.requirers_data:
                # Duplicate backend names check is done in the library's `get_data` method
                backend_names.add(requirer.application_data.service)

                if requirer.application_data.rate_limit:
                    stick_table_entries.append(f"{requirer.application_data.service}_rate_limit")

                backend = HAProxyRouteBackend(
                    relation_id=requirer.relation_id,
                    application_data=requirer.application_data,
                    servers=get_servers_definition_from_requirer_data(requirer),
                    external_hostname=external_hostname,
                )

                if not backend.hostname_acls:
                    relation_ids_with_invalid_data.append(requirer.relation_id)
                    continue

                if (
                    backend.servers
                    and backend.servers[0].protocol == "https"
                    and not ca_certs_configured
                ):
                    relation_ids_with_invalid_data.append(requirer.relation_id)
                    continue

                backends.append(backend)

            tcp_endpoints: list[HAProxyRouteTcpEndpoint] = []
            tcp_requirers: HaproxyRouteTcpRequirersData = haproxy_route_tcp.get_data(
                haproxy_route_tcp.relations
            )
            relation_ids_with_invalid_data_tcp = tcp_requirers.relation_ids_with_invalid_data
            for tcp_requirer in tcp_requirers.requirers_data:
                if haproxy_route.relations and tcp_requirer.application_data.port in [80, 443]:
                    logger.error("port 80 and 443 are not allowed if haproxy_route is present.")
                    relation_ids_with_invalid_data_tcp.append(tcp_requirer.relation_id)
                    continue
                tcp_endpoints.append(
                    HAProxyRouteTcpEndpoint.from_haproxy_route_tcp_requirer_data(tcp_requirer)
                )

            return HaproxyRouteRequirersInformation(
                # Sort backend by the max depth of the required path.
                # This is to ensure that backends with deeper path ACLs get routed first.
                backends=sorted(backends, key=get_backend_max_path_depth, reverse=True),
                stick_table_entries=stick_table_entries,
                peers=[cast(IPvAnyAddress, peer_address) for peer_address in peers],
                relation_ids_with_invalid_data=relation_ids_with_invalid_data,
                relation_ids_with_invalid_data_tcp=relation_ids_with_invalid_data_tcp,
                tcp_endpoints=tcp_endpoints,
            )
        except DataValidationError as exc:
            # This exception is only raised if the provider has "raise_on_validation_error" set
            raise HaproxyRouteIntegrationDataValidationError from exc

    @model_validator(mode="after")
    def check_backend_paths(self) -> Self:
        """Output a warning if requirers declared conflicting paths/hostnames.

        Returns:
            Self: The validated model.
        """
        requirers_paths: list[str] = []
        requirers_hostnames: list[str] = []

        for backend in self.backends:
            requirers_paths.extend(backend.application_data.paths)
            requirers_hostnames.extend(backend.hostname_acls)

        if len(requirers_paths) != len(set(requirers_paths)):
            logger.warning(
                "Requirers defined path(s) that map to multiple backends."
                "This can cause unintended behaviors."
            )

        if len(requirers_hostnames) != len(set(requirers_hostnames)):
            logger.warning(
                "Requirers defined hostname(s) that map to multiple backends."
                "This can cause unintended behaviors."
            )
        return self

    @property
    def acls_for_allow_http(self) -> list[str]:
        """Get the list of all allow_http ACLs from all backends.

        Returns:
            list[str]: List of allow_http ACLs.
        """
        allow_http_acls: list[str] = []
        for backend in self.backends:
            if backend.application_data.allow_http:
                acl = f"{{ req.hdr(Host) -m str {' '.join(backend.hostname_acls)} }}"
                if backend.path_acl_required:
                    acl += f" {{ path_beg -i {' '.join(backend.application_data.paths)} }}"
                if backend.deny_path_acl_required:
                    acl += f" !{{ path_beg -i {' '.join(backend.application_data.deny_paths)} }}"
                allow_http_acls.append(acl)
        return allow_http_acls


def get_servers_definition_from_requirer_data(
    requirer: HaproxyRouteRequirerData,
) -> list[HAProxyRouteServer]:
    """Get servers definition from the requirer data.

    Args:
        requirer: The requirer data.

    Returns:
        list[HAProxyRouteServer]: List of server definitions.
    """
    servers: list[HAProxyRouteServer] = []
    server_addresses: list[IPvAnyAddress] = (
        requirer.application_data.hosts
        if requirer.application_data.hosts
        else [unit_data.address for unit_data in requirer.units_data]
    )
    for i, server_address in enumerate(server_addresses):
        for port in requirer.application_data.ports:
            servers.append(
                HAProxyRouteServer(
                    server_name=f"{requirer.application_data.service}_{port}_{i}",
                    address=server_address,
                    port=port,
                    protocol=requirer.application_data.protocol,
                    check=requirer.application_data.check,
                    maxconn=requirer.application_data.server_maxconn,
                    external_grpc_port=requirer.application_data.external_grpc_port,
                )
            )
    return servers


def get_backend_max_path_depth(backend: HAProxyRouteBackend) -> int:
    """Return the max depth of requested paths for the given backend.

    Return 1 if no custom path is requested.

    Args:
        backend: haproxy-route backend.

    Returns:
        int: The max requested path depth
    """
    paths = backend.application_data.paths
    if not paths:
        return 1
    return max(len(path.rstrip("/").split("/")) for path in paths)
