# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy route charm state component."""

from functools import cached_property
from typing import Optional, Self, cast

from charms.haproxy.v0.haproxy_route_tcp import (
    HaproxyRouteTcpRequirerData,
    TCPHealthCheckType,
    TCPServerHealthCheck,
)
from pydantic import Field, IPvAnyAddress
from pydantic.dataclasses import dataclass
from typing_extensions import NamedTuple

from .exception import CharmStateValidationBaseError


class HAProxyRouteTcpFrontendValidationError(CharmStateValidationBaseError):
    """Exception raised when a TCP frontend is not valid."""


class BackendRoutingConfiguration(NamedTuple):
    """A representation of backend routing configuration.
    Attrs:
        acl: The ACL condition for routing.
        use_backend: haproxy use_backend configuration.
    """

    acl: str
    use_backend: str


@dataclass(frozen=True)
class HaproxyRouteTcpServer:
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
    check: Optional[TCPServerHealthCheck]
    maxconn: Optional[int]


@dataclass
class HAProxyRouteTcpBackend(HaproxyRouteTcpRequirerData):
    """Represent an endpoint for haproxy-route-tcp.

    Attrs:
        consistent_hashing: Whether consistent hashing should be applied for this backend.
        servers: List of backend servers for this TCP endpoint.
        name: Unique name for this TCP endpoint.
        tcp_check_options: TCP health check options for HAProxy configuration.
    """

    @classmethod
    def from_haproxy_route_tcp_requirer_data(cls, provider: HaproxyRouteTcpRequirerData) -> "Self":
        """Instantiate a HAProxyRouteTcpBackend class from the parent class.

        Args:
            provider: parent class.

        Returns:
            Self: The instantiated HAProxyRouteTcpBackend class.
        """
        return cls(
            relation_id=provider.relation_id,
            application_data=provider.application_data,
            application=provider.application,
            units_data=provider.units_data,
        )

    @property
    def consistent_hashing(self) -> bool:
        """Indicate if consistent hashing should be applied for this backend.

        We make the assumption that the data has been validated by the library.

        Returns:
            bool: Whether consistent hashing should be applied.
        """
        if load_balancing := self.application_data.load_balancing:
            return load_balancing.consistent_hashing
        return False

    @cached_property
    def servers(self) -> list[HaproxyRouteTcpServer]:
        """Get the list of backend servers for this TCP endpoint.

        Creates HaproxyRouteTcpServer instances from the unit data, assigning
        sequential server names and using the application's backend port and
        health check configuration.

        Returns:
            list[HaproxyRouteTcpServer]: List of configured backend servers.
        """
        servers = []
        backend_addresses = self.application_data.hosts
        if not backend_addresses:
            backend_addresses = [unit_data.address for unit_data in self.units_data]

        for i, address in enumerate(backend_addresses):
            servers.append(
                HaproxyRouteTcpServer(
                    server_name=f"{self.application}-{i}",
                    port=cast(int, self.application_data.backend_port),
                    address=address,
                    check=self.application_data.check,
                    maxconn=self.application_data.server_maxconn,
                )
            )
        return servers

    @property
    def name(self) -> str:
        """Get the unique name for this TCP endpoint.

        Combines the application name and frontend port to create a unique
        identifier for the HAProxy configuration section.

        Returns:
            str: The endpoint name in format "{application}_{port}".
        """
        return f"{self.application}_{self.application_data.port}"

    @property
    def tcp_check_options(self) -> list[str]:
        """Get the TCP health check options for HAProxy configuration.

        Generates the appropriate HAProxy configuration lines for TCP health
        checks based on the check type. For generic checks, creates send/expect
        options. For database checks, includes the database user if specified.

        Returns:
            list[str]: List of HAProxy TCP check configuration options.
        """
        if check := self.application_data.check:
            if check.check_type == TCPHealthCheckType.GENERIC:
                options = ["option tcp-check"]
                if send := self.application_data.check.send:
                    options.append(f"tcp-check send {send!r}")
                if expect := self.application_data.check.expect:
                    options.append(f"tcp-check expect string {expect!r}")
                return options
            if check.check_type in [TCPHealthCheckType.POSTGRES, TCPHealthCheckType.MYSQL]:
                db_user = f" {check.db_user}" if check.db_user else ""
                return [f"option {check.check_type!s}{db_user}"]
            if check.check_type is not None:
                return [f"option {check.check_type!s}"]
        return []


@dataclass
class HAProxyRouteTcpFrontend:
    """A representation of a TCP frontend in the haproxy config.

    Attrs:
        port: The port exposed on the provider.
        backends: List of backend endpoints for this frontend.
        enforce_tls: Whether to enforce TLS for all traffic.
        tls_terminate: Whether to enable TLS termination.
    """

    port: int = Field(description="The port exposed on the provider.", gt=0, le=65535)
    backends: list[HAProxyRouteTcpBackend] = Field(description="List of backend endpoints.")
    enforce_tls: bool = Field(description="Whether to enforce TLS for all traffic.", default=True)
    tls_terminate: bool = Field(description="Whether to enable tls termination.", default=True)
    relation_ids_with_invalid_data: set[int] = Field(
        description="List of relation ids with invalid data.", default=set[int]()
    )

    @classmethod
    def from_backends(cls, backends: list[HAProxyRouteTcpBackend]) -> "Self":
        """Instantiate a HAProxyRouteTcpFrontend class from a list of backends.

        Args:
            backends: List of backend endpoints.

        Raises:
            HAProxyRouteTcpFrontendValidationError: When the frontend is initialized with no backends.

        Returns:
            Self: The instantiated HAProxyRouteTcpFrontend class.
        """
        # If there's only one backend, return the class directly with values from the backend
        if len(backends) == 1:
            return cls(
                port=backends[0].application_data.port,
                backends=backends,
                enforce_tls=backends[0].application_data.enforce_tls,
                tls_terminate=backends[0].application_data.tls_terminate,
                relation_ids_with_invalid_data=set[int](),
            )

        # At this point we have more than one backend, all of them need to set enforce_tls=True
        # and have an sni value for them to be routable and merged.
        # If there are backends that set tls_terminate=True amongst the routable backends
        # then only those will be merged.
        routable_backends_with_tls_terminate: list[HAProxyRouteTcpBackend] = []
        routable_backends_without_tls_terminate: list[HAProxyRouteTcpBackend] = []

        relation_ids_with_invalid_data: set[int] = set[int]()
        for backend in backends:
            if not backend.application_data.enforce_tls or backend.application_data.sni is None:
                relation_ids_with_invalid_data.add(backend.relation_id)
                continue

            if backend.application_data.tls_terminate:
                routable_backends_with_tls_terminate.append(backend)
            else:
                routable_backends_without_tls_terminate.append(backend)

        if routable_backends_with_tls_terminate:
            relation_ids_with_invalid_data.update(
                backend.relation_id for backend in routable_backends_without_tls_terminate
            )

        rendered_backends = (
            routable_backends_with_tls_terminate or routable_backends_without_tls_terminate
        )
        if not rendered_backends:
            raise HAProxyRouteTcpFrontendValidationError(
                "Cannot create HAProxyRouteTcpFrontend from empty backends list"
            )
        return cls(
            port=rendered_backends[0].application_data.port,
            backends=rendered_backends,
            enforce_tls=rendered_backends[0].application_data.enforce_tls,
            tls_terminate=rendered_backends[0].application_data.tls_terminate,
            relation_ids_with_invalid_data=relation_ids_with_invalid_data,
        )

    @property
    def backend_sni_routing_configurations(self) -> list[BackendRoutingConfiguration]:
        """Get the routing configuration for each backend.

        Returns:
            list[BackendRoutingConfiguration]: List of SNI ACL and use_backend configuration.
        """
        acls: list[BackendRoutingConfiguration] = []
        for backend in self.backends:
            if sni := backend.application_data.sni:
                sni_fetch_method = (
                    "ssl_fc_sni" if backend.application_data.tls_terminate else "req.ssl_sni"
                )
                acls.append(
                    BackendRoutingConfiguration(
                        acl=f"acl is_{backend.name} {sni_fetch_method} -i {sni}",
                        use_backend=f"use_backend {backend.name} if is_{backend.name}",
                    )
                )
        return acls

    @property
    def is_sni_routing_enabled(self) -> bool:
        """Indicate if SNI routing is enabled for this frontend.

        If SNI routing is enabled, haproxy needs to be configured with:
        ```
        tcp-request inspect-delay 5s
        tcp-request content accept if { req_ssl_hello_type 1 }
        ```
        to properly inspect and route traffic based on the SNI value.

        Returns:
            bool: Whether SNI routing is enabled.
        """
        return bool(self.backend_sni_routing_configurations)

    @property
    def default_backend_name(self) -> str:
        """Get the default backend name for this frontend.

        The default backend is used when no SNI ACLs match.

        Returns:
            str: The name of the default backend.
        """
        return f"haproxy_route_tcp_{self.port}_default_backend"

    @property
    def content_inspect_delay_required(self) -> bool:
        """Indicate if content inspect delay is required.

        This will add `tcp-request inspect-delay 5s` to the frontend configuration.

        Returns:
            bool: Whether content inspect delay is required.
        """
        return self.is_sni_routing_enabled or self.enforce_tls

    @property
    def enforce_tls_configuration(self) -> str:
        """Get the enforce TLS configuration line.

        This will add `tcp-request content reject unless { req_ssl_hello_type 1 }`
        to the frontend configuration if sni is not used, otherwise we can simply
        do `tcp-request content reject` to not have to reevaluate the SNI ACL.

        Returns:
            str: The enforce TLS configuration line.
        """
        if not self.is_sni_routing_enabled:
            return "tcp-request content reject unless { req_ssl_hello_type 1 }"
        return "tcp-request content reject"

    @property
    def default_backend(self) -> HAProxyRouteTcpBackend | None:
        """Return the backend used as the default backend if it is not empty.

        The default backend is not empty if there is exactly one backend and that
        backend does not use SNI routing. This means that all traffic coming into
        the frontend will be routed to that backend.

        An empty default backend will have no servers and reject all TCP connections.

        Returns:
            HAProxyRouteTcpBackend | None: The default backend if it is not empty, otherwise None.
        """
        if len(self.backends) == 1 and not self.is_sni_routing_enabled:
            return self.backends[0]
        return None
