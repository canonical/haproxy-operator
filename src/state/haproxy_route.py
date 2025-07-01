# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy route charm state component."""

import logging
from functools import cached_property
from typing import Optional, cast

from charms.haproxy.v0.haproxy_route import (
    DataValidationError,
    HaproxyRewriteMethod,
    HaproxyRouteProvider,
    HaproxyRouteRequirerData,
    LoadBalancingAlgorithm,
    RequirerApplicationData,
    ServerHealthCheck,
)
from pydantic import IPvAnyAddress, model_validator
from pydantic.dataclasses import dataclass
from typing_extensions import Self

from state.tls import TLSInformation

from .exception import CharmStateValidationBaseError

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
        check: Health check configuration.
        maxconn: Maximum allowed connections before requests are queued.
    """

    server_name: str
    address: IPvAnyAddress
    port: int
    check: ServerHealthCheck
    maxconn: Optional[int]


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
    """

    relation_id: int
    application_data: RequirerApplicationData
    servers: list[HAProxyRouteServer]
    external_hostname: str

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

        Appends subdomain to the configured external_hostname.
        For example, with the configured hostname of `haproxy.internal`, and requested subdomains
        ['api'] will result in the following haproxy ACL:

        acl acl_host_<backend_name> req.hdr(Host) -m str api.haproxy.internal

        Returns:
            list[str]: List of hostname for ACL matching.
        """
        if not self.application_data.subdomains:
            return [self.external_hostname]

        return list(
            map(
                lambda subdomain: (
                    f"{cast(str, subdomain).rstrip('.')}.{self.external_hostname}"
                    if subdomain
                    else self.external_hostname
                ),
                self.application_data.subdomains,
            )
        )

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
            return f"hash req.cookie({cast(str, self.application_data.load_balancing.cookie)})"
        return str(self.application_data.load_balancing.algorithm.value)

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
                    f"{str(rewrite.method)} {rewrite.header} {rewrite.expression}"
                )
                continue
            rewrite_configurations.append(f"{str(rewrite.method.value)} {rewrite.expression}")
        return rewrite_configurations


@dataclass(frozen=True)
class HaproxyRouteRequirersInformation:
    """A component of charm state containing haproxy-route requirers information.

    Attrs:
        backends: The list of backends each corresponds to a requirer application.
        stick_table_entries: List of stick table entries in the haproxy "peer" section.
        peers: List of IP address of haproxy peer units.
    """

    backends: list[HAProxyRouteBackend]
    stick_table_entries: list[str]
    peers: list[IPvAnyAddress]

    @classmethod
    def from_provider(
        cls, haproxy_route: HaproxyRouteProvider, tls_information: TLSInformation, peers: list[str]
    ) -> "HaproxyRouteRequirersInformation":
        """Initialize the HaproxyRouteRequirersInformation state component.

        Args:
            haproxy_route: The haproxy-route provider class.
            tls_information: The charm's TLS information state component.
            peers: List of IP address of haproxy peer units.

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
            for requirer in requirers.requirers_data:
                # Duplicate backend names check is done in the library's `get_data` method
                backend_names.add(requirer.application_data.service)

                if requirer.application_data.rate_limit:
                    stick_table_entries.append(f"{requirer.application_data.service}_rate_limit")

                backend = HAProxyRouteBackend(
                    relation_id=requirer.relation_id,
                    application_data=requirer.application_data,
                    servers=get_servers_definition_from_requirer_data(requirer),
                    external_hostname=tls_information.external_hostname,
                )
                backends.append(backend)

            return HaproxyRouteRequirersInformation(
                # Sort backend by the max depth of the required path.
                # This is to ensure that backends with deeper path ACLs get routed first.
                backends=sorted(backends, key=get_backend_max_path_depth, reverse=True),
                stick_table_entries=stick_table_entries,
                peers=[cast(IPvAnyAddress, peer_address) for peer_address in peers],
            )
        except DataValidationError as exc:
            # This exception is only raised if the provider has "raise_on_validation_error" set
            raise HaproxyRouteIntegrationDataValidationError from exc

    @model_validator(mode="after")
    def check_backend_paths(self) -> Self:
        """Output a warning if requirers declared conflicting paths/subdomains.

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
                (
                    "Requirers defined path(s) that map to multiple backends."
                    "This can cause unintended behaviours."
                )
            )

        if len(requirers_hostnames) != len(set(requirers_hostnames)):
            logger.warning(
                (
                    "Requirers defined hostname(s) that map to multiple backends."
                    "This can cause unintended behaviours."
                )
            )
        return self


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
    for i, unit_data in enumerate(requirer.units_data):
        for port in requirer.application_data.ports:
            servers.append(
                HAProxyRouteServer(
                    server_name=f"{requirer.application_data.service}_{port}_{i}",
                    address=unit_data.address,
                    port=port,
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
