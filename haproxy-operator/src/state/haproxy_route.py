# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy route charm state component."""

import logging
from collections import defaultdict
from collections.abc import Collection
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
from .haproxy_route_tcp import (
    HAProxyRouteTcpBackend,
    HAProxyRouteTcpFrontend,
    HAProxyRouteTcpFrontendValidationError,
)

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
    """

    server_name: str
    address: IPvAnyAddress
    port: int
    protocol: str
    check: Optional[ServerHealthCheck]
    maxconn: Optional[int]


@dataclass(frozen=True)
class HAProxyRouteBackend:
    """A component of charm state that represent an ingress requirer application.

    Attrs:
        relation_id: The id of the relation, used to publish the proxied endpoints.
        application_data: requirer application data.
        backend_name: The name of the backend (computed).
        servers: The list of server each corresponding to a requirer unit.
        hostname_acls: The list of hostname ACLs for the backend.
        load_balancing_configuration: Load balancing configuration for the haproxy backend.
        rewrite_configurations: Rewrite configuration.
        path_acl_required: Indicate if path routing is required.
        deny_path_acl_required: Indicate if deny_path is required.
        consistent_hashing: Use consistent hashing to avoid redirection
            when servers are added/removed.
        wildcard_hostname_acls: The set of wildcard hostname ACLs for the backend.
        standard_hostname_acls: The set of standard (non-wildcard) hostname ACLs for the backend.
        health_check_host_header: The Host header to use for health checks.
    """

    relation_id: int
    application_data: RequirerApplicationData
    servers: list[HAProxyRouteServer]
    hostname_acls: set[str]

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

    def _build_rewrite_configurations(
        self, allowed_methods: Collection[HaproxyRewriteMethod] | None = None
    ) -> list[str]:
        """Build rewrite configurations with optional filtering.

        Args:
            allowed_methods: Optional collection of allowed rewrite methods to filter by.

        Returns:
            list[str]: The rewrite configurations.
        """
        rewrite_configurations: list[str] = []
        for rewrite in self.application_data.rewrites:
            if allowed_methods and rewrite.method not in allowed_methods:
                continue

            match rewrite.method:
                case HaproxyRewriteMethod.SET_HEADER:
                    rewrite_configurations.append(
                        f"{rewrite.method.value!s} {rewrite.header} {rewrite.expression}"
                    )
                case HaproxyRewriteMethod.SET_PATH | HaproxyRewriteMethod.SET_QUERY:
                    rewrite_configurations.append(f"{rewrite.method.value!s} {rewrite.expression}")
        return rewrite_configurations

    @cached_property
    def rewrite_configurations(self) -> list[str]:
        """Build the rewrite configurations.

        For example, method = SET_HEADER, header = COOKIE, expression = "testing"
        will result in the following rewrite config:

        http-request set-header COOKIE testing

        Returns:
            list[str]: The rewrite configurations.
        """
        return self._build_rewrite_configurations()

    @cached_property
    def grpc_rewrite_configurations(self) -> list[str]:
        """Build rewrite configurations for header rewrites only.

        Returns:
            list[str]: The header-only rewrite configurations.
        """
        return self._build_rewrite_configurations(
            allowed_methods={HaproxyRewriteMethod.SET_HEADER, HaproxyRewriteMethod.SET_PATH}
        )

    @property
    def wildcard_hostname_acls(self) -> set[str]:
        """Build the hostname-based routing rules for this backend.

        Returns:
            set[str]: The hostname-based routing rules for this backend (non-wildcard).
        """
        return {hostname[2:] for hostname in self.hostname_acls if hostname.startswith("*.")}

    @property
    def standard_hostname_acls(self) -> set[str]:
        """Build the hostname ACLs for this backend that are not wildcard.

        Returns:
            set[str]: The hostname ACLs for this backend that are wildcard.
        """
        return self.hostname_acls - self.wildcard_hostname_acls

    @property
    def health_check_host_header(self) -> Optional[str]:
        """Build the backend health check Host header.

        Returns:
            Optional[str]: The base domain if the hostname is a wildcard,
            otherwise return the hostname itself.
        """
        if not self.hostname_acls:
            return None
        hostname = next(iter(self.hostname_acls))
        return hostname[2:] if hostname.startswith("*.") else hostname


# pylint: disable=too-many-locals
@dataclass(frozen=True)
class HaproxyRouteRequirersInformation:
    """A component of charm state containing haproxy-route requirers information.

    Attrs:
        backends: The list of backends each corresponds to a requirer application.
        stick_table_entries: List of stick table entries in the haproxy "peer" section.
        peers: List of IP address of haproxy peer units.
        relation_ids_with_invalid_data: Set of haproxy-route relation ids
            that contains invalid data.
        relation_ids_with_invalid_data_tcp: Set of haproxy-route-tcp relation ids
            that contains invalid data.
        ports_with_conflicts: Set of ports that have conflicts between HTTP, TCP, and gRPC backends.
        tcp_frontends: List of frontend in TCP mode.
    """

    backends: list[HAProxyRouteBackend]
    stick_table_entries: list[str]
    peers: list[IPvAnyAddress]
    relation_ids_with_invalid_data: set[int]
    relation_ids_with_invalid_data_tcp: set[int]
    ports_with_conflicts: set[int]
    tcp_frontends: list[HAProxyRouteTcpFrontend] = Field(strict=False)

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
                    hostname_acls=generate_hostname_acls(
                        requirer.application_data, external_hostname
                    ),
                )

                if not backend.hostname_acls:
                    relation_ids_with_invalid_data.add(requirer.relation_id)
                    continue

                if (
                    backend.servers
                    and backend.servers[0].protocol == "https"
                    and not ca_certs_configured
                ):
                    relation_ids_with_invalid_data.add(requirer.relation_id)
                    continue

                backends.append(backend)

            tcp_frontends: list[HAProxyRouteTcpFrontend] = []
            tcp_requirers: HaproxyRouteTcpRequirersData = haproxy_route_tcp.get_data(
                haproxy_route_tcp.relations
            )
            tcp_frontends = parse_haproxy_route_tcp_requirers_data(tcp_requirers)
            # Calculate the invalid relation ids after parsing the relations data into
            # HAProxyRouteTcpFrontend objects
            relation_ids_with_invalid_data_tcp = (
                tcp_requirers.relation_ids_with_invalid_data.union(
                    *[frontend.relation_ids_with_invalid_data for frontend in tcp_frontends]
                )
            )

            return HaproxyRouteRequirersInformation(
                # Sort backend by the max depth of the required path.
                # This is to ensure that backends with deeper path ACLs get routed first.
                backends=sorted(backends, key=get_backend_max_path_depth, reverse=True),
                stick_table_entries=stick_table_entries,
                peers=[cast(IPvAnyAddress, peer_address) for peer_address in peers],
                relation_ids_with_invalid_data=relation_ids_with_invalid_data,
                relation_ids_with_invalid_data_tcp=relation_ids_with_invalid_data_tcp,
                tcp_frontends=tcp_frontends,
                ports_with_conflicts=set[int](),
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

    @model_validator(mode="after")
    def check_tcp_http_port_conflicts(self) -> Self:
        """Check for port conflicts between HTTP backends and TCP/gRPC backends.
        If conflict between HTTP and TCP/gRPC backends is found,
        the TCP/gRPC backend relation_id is added to the invalid data list.
        If conflict between TCP and gRPC backends is found,
        both relation_ids are added to the invalid data lists.

        Returns:
            Self: The validated model
        """
        standard_ports = {80, 443}
        valid_backends = self.valid_backends()
        has_http_backends = any(not b.application_data.external_grpc_port for b in valid_backends)

        grpc_ports = {
            backend.application_data.external_grpc_port: backend
            for backend in valid_backends
            if backend.application_data.external_grpc_port
        }
        tcp_ports = {frontend.port: frontend for frontend in self.tcp_frontends}

        # Check for conflicts between standard HTTP and TCP/gRPC ports
        if has_http_backends:
            for standard_port in standard_ports:
                if standard_port in tcp_ports:
                    logger.error(
                        f"TCP backend conflicts with HTTP backends on external port {standard_port}."
                    )
                    self.relation_ids_with_invalid_data_tcp.update(
                        {backend.relation_id for backend in tcp_ports[standard_port].backends}
                    )
                    self.ports_with_conflicts.add(standard_port)
                if standard_port in grpc_ports:
                    logger.error(
                        f"gRPC backend conflicts with HTTP backends on external port {standard_port}."
                    )
                    self.relation_ids_with_invalid_data.add(grpc_ports[standard_port].relation_id)
                    self.ports_with_conflicts.add(standard_port)

        # Check for conflicts between gRPC and TCP ports
        for port in grpc_ports.keys() & tcp_ports.keys():
            logger.error(f"Conflicting TCP backend and gRPC backend on external port {port}.")
            self.relation_ids_with_invalid_data_tcp.update(
                {backend.relation_id for backend in tcp_ports[port].backends}
            )
            self.relation_ids_with_invalid_data.add(grpc_ports[port].relation_id)
            self.ports_with_conflicts.add(port)

        if self.ports_with_conflicts:
            logger.warning(f"The following ports have conflicts: {self.ports_with_conflicts}")

        return self

    def valid_backends(self) -> list[HAProxyRouteBackend]:
        """Get the list of valid backends (not in the invalid list).

        Returns:
            list[HAProxyRouteBackend]: List of valid backends.
        """
        return [
            backend
            for backend in self.backends
            if backend.relation_id not in self.relation_ids_with_invalid_data
        ]

    def valid_tcp_frontends(self) -> list[HAProxyRouteTcpFrontend]:
        """Get the list of valid TCP endpoints (not in the invalid list).

        Returns:
            list[HAProxyRouteTcpFrontend]: List of valid TCP endpoints.
        """
        return [
            frontend
            for frontend in self.tcp_frontends
            if frontend.port not in self.ports_with_conflicts
        ]

    @property
    def acls_for_allow_http(self) -> list[str]:
        """Get the list of all allow_http ACLs from all backends.

        Returns:
            list[str]: List of allow_http ACLs.
        """
        allow_http_acls: list[str] = []
        for backend in self.backends:
            if backend.application_data.allow_http:
                acl = f"{{ req.hdr(host),field(1,:) -i {' '.join(backend.hostname_acls)} }}"
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


def generate_hostname_acls(
    application_data: RequirerApplicationData, external_hostname: Optional[str]
) -> set[str]:
    """Generate the list of hostname ACLs for a backend.

    Args:
        application_data: The requirer application data.
        external_hostname: The charm's configured external hostname.

    Returns:
        set[str]: The combined set of hostnames.
    """
    if not application_data.hostname:
        if not external_hostname:
            return set()

        return {external_hostname}
    return {application_data.hostname, *application_data.additional_hostnames}


def parse_haproxy_route_tcp_requirers_data(
    tcp_requirers: HaproxyRouteTcpRequirersData,
) -> list[HAProxyRouteTcpFrontend]:
    """Parse HAProxyRouteTcpFrontend data from requirers into frontend objects.

    Returns:
        list[HAProxyRouteTcpFrontend]: The parsed frontend data.
    """
    port_to_backends_mapping: dict[int, list[HAProxyRouteTcpBackend]] = defaultdict(list)
    for requirer in tcp_requirers.requirers_data:
        endpoint = HAProxyRouteTcpBackend.from_haproxy_route_tcp_requirer_data(requirer)
        port_to_backends_mapping[endpoint.application_data.port].append(endpoint)
    tcp_frontends: list[HAProxyRouteTcpFrontend] = []
    for backends in port_to_backends_mapping.values():
        try:
            frontend = HAProxyRouteTcpFrontend.from_backends(backends)
            tcp_frontends.append(frontend)
        except HAProxyRouteTcpFrontendValidationError as exc:
            logger.error(f"Failed to parse TCP frontend: {exc}")
            continue
    return tcp_frontends
