# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAproxy route charm state component."""

from functools import cached_property
from typing import Optional, Self

from charms.haproxy.v1.haproxy_route_tcp import (
    HaproxyRouteTcpRequirerData,
    PortRange,
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
        send_proxy: Whether to enable PROXY protocol for this server.
    """

    server_name: str
    address: IPvAnyAddress
    port: int | None
    check: Optional[TCPServerHealthCheck]
    maxconn: Optional[int]
    send_proxy: bool = False

    @property
    def server_endpoint(self) -> str:
        """Get the server endpoint in "address:port" format.

        Returns:
            str: The server endpoint.
        """
        if self.port is not None:
            return f"{self.address}:{self.port}"
        return str(self.address)


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
        sequential server names and the health check configuration. Servers have
        no explicit port: the backend destination port is derived from the
        connection destination port (translated by the port mapping offset when
        needed), so the same backend can serve a whole port range.

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
                    port=None,
                    address=address,
                    check=self.application_data.check,
                    maxconn=self.application_data.server_maxconn,
                    send_proxy=self.application_data.proxy_protocol,
                )
            )
        return servers

    @property
    def dst_port_translation(self) -> Optional[str]:
        """Get the HAProxy directive that translates the destination port.

        When the frontend and backend ranges have an offset (e.g. the requirer
        maps frontend port 8080 to backend port 9090), HAProxy must rewrite the
        connection destination port before forwarding to the backend servers.

        Returns:
            Optional[str]: The `tcp-request content set-dst-port` directive, or
                None when no translation is required (offset is zero).
        """
        offset = self.application_data.effective_port_mapping.offset
        if offset > 0:
            return f"tcp-request content set-dst-port dst_port,add({offset})"
        if offset < 0:
            return f"tcp-request content set-dst-port dst_port,sub({abs(offset)})"
        return None

    @property
    def name(self) -> str:
        """Get the unique name for this TCP endpoint.

        Combines the application name and frontend port range to create a unique
        identifier for the HAProxy configuration section.

        Returns:
            str: The endpoint name in format "{application}_{start}_{end}".
        """
        port_range = self.application_data.port_range
        return f"{self.application}_{port_range.start}_{port_range.end}"

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

    @property
    def is_wildcard_sni(self) -> bool:
        """Check if the SNI is a wildcard pattern.

        Returns:
            bool: True if SNI starts with "*.", False otherwise.
        """
        return self.application_data.sni is not None and self.application_data.sni.startswith("*.")

    @property
    def sni_match_rule(self) -> Optional[str]:
        """Get the SNI match rule for HAProxy ACL.

        Returns the appropriate match rule based on whether the SNI is a wildcard:
        - For wildcard SNI (*.example.com): "-m end .example.com"
        - For standard SNI (api.example.com): "-i api.example.com"

        Returns:
            Optional[str]: The match rule string, or None if SNI is not set.
        """
        if self.application_data.sni is None:
            return None
        if self.is_wildcard_sni:
            return f"-m end {self.application_data.sni[1:]}"
        return f"-i {self.application_data.sni}"


@dataclass
class HAProxyRouteTcpFrontend:
    """A representation of a TCP frontend in the haproxy config.

    Attrs:
        port: The port exposed on the provider.
        backends: List of backend endpoints for this frontend.
        default_backend: The catch-all backend, or None for an empty rejecting backend.
        enforce_tls: Whether to enforce TLS for all traffic.
        tls_terminate: Whether to enable TLS termination.
    """

    port_range: PortRange = Field(description="The port(s) exposed on the provider.")
    backends: list[HAProxyRouteTcpBackend] = Field(description="List of backend endpoints.")
    default_backend: Optional[HAProxyRouteTcpBackend] = Field(
        description="The catch-all backend, or None for an empty rejecting backend."
    )
    enforce_tls: bool = Field(description="Whether to enforce TLS for all traffic.", default=True)
    tls_terminate: bool = Field(description="Whether to enable tls termination.", default=True)
    relation_ids_with_invalid_data: set[int] = Field(
        description="List of relation ids with invalid data.", default=set[int]()
    )

    @staticmethod
    def _partition_routable_single_backends(
        backends: list[HAProxyRouteTcpBackend],
    ) -> tuple[list[HAProxyRouteTcpBackend], list[HAProxyRouteTcpBackend], set[int]]:
        """Partition single-port backends by SNI-routability and TLS termination.

        A single-port backend is SNI-routable only if it enforces TLS and declares
        an sni value. Routable backends are further split by whether they terminate
        TLS, because a frontend cannot mix terminating and non-terminating backends.

        Args:
            backends: The single-port backends to partition.

        Returns:
            tuple: (routable backends that terminate TLS, routable backends that
                don't, relation IDs of backends that are not SNI-routable).
        """
        with_tls_terminate: list[HAProxyRouteTcpBackend] = []
        without_tls_terminate: list[HAProxyRouteTcpBackend] = []
        non_routable_ids: set[int] = set[int]()
        for backend in backends:
            if not backend.application_data.enforce_tls or backend.application_data.sni is None:
                non_routable_ids.add(backend.relation_id)
                continue
            if backend.application_data.tls_terminate:
                with_tls_terminate.append(backend)
            else:
                without_tls_terminate.append(backend)
        return with_tls_terminate, without_tls_terminate, non_routable_ids

    @classmethod
    def from_backends_single_port(cls, backends: list[HAProxyRouteTcpBackend]) -> "Self":
        """Instantiate a frontend that listens on a single port.

        A lone backend becomes the default backend and does not require an SNI.
        When several single-port backends share the port they are merged and routed
        by SNI, so each must enforce TLS and declare an sni value. If some backends
        terminate TLS and others don't, only the terminating ones are merged.

        Args:
            backends: List of single-port backend endpoints sharing the same port.

        Raises:
            HAProxyRouteTcpFrontendValidationError: When no routable backend remains.

        Returns:
            Self: The instantiated HAProxyRouteTcpFrontend class.
        """
        if not backends:
            raise HAProxyRouteTcpFrontendValidationError(
                "Cannot create HAProxyRouteTcpFrontend from empty backends list"
            )

        # A single backend is always routable on its own (no SNI required).
        if len(backends) == 1:
            backend = backends[0]
            return cls(
                port_range=backend.application_data.port_range,
                backends=backends,
                # Without an SNI the lone backend serves all traffic; with an SNI it
                # is routed by the SNI ACL and the default backend rejects the rest.
                default_backend=backend if backend.sni_match_rule is None else None,
                enforce_tls=backend.application_data.enforce_tls,
                tls_terminate=backend.application_data.tls_terminate,
                relation_ids_with_invalid_data=set[int](),
            )

        with_tls_terminate, without_tls_terminate, relation_ids_with_invalid_data = (
            cls._partition_routable_single_backends(backends)
        )
        # If there are backends that set tls_terminate=True amongst the routable
        # backends then only those will be merged.
        if with_tls_terminate:
            relation_ids_with_invalid_data.update(
                backend.relation_id for backend in without_tls_terminate
            )
            rendered_backends = with_tls_terminate
        else:
            rendered_backends = without_tls_terminate

        if not rendered_backends:
            raise HAProxyRouteTcpFrontendValidationError(
                "Cannot create HAProxyRouteTcpFrontend from empty backends list"
            )
        return cls(
            port_range=rendered_backends[0].application_data.port_range,
            backends=rendered_backends,
            # Several backends share the port and are routed by SNI, so the default
            # backend is empty and rejects traffic that matches no SNI ACL.
            default_backend=None,
            enforce_tls=rendered_backends[0].application_data.enforce_tls,
            tls_terminate=rendered_backends[0].application_data.tls_terminate,
            relation_ids_with_invalid_data=relation_ids_with_invalid_data,
        )

    @classmethod
    def from_backends_port_range(
        cls,
        range_backend: HAProxyRouteTcpBackend,
        single_backends: list[HAProxyRouteTcpBackend],
    ) -> "Self":
        """Instantiate a frontend that binds on a port range.

        The port-range backend acts as the catch-all default backend (no SNI
        required) and fixes the frontend's TLS termination mode. Single-port backends
        whose port falls within the range can be merged in and are routed by SNI, so
        they must enforce TLS, declare an sni value, and match the anchor's TLS
        termination mode.

        Args:
            range_backend: The port-range backend anchoring the frontend.
            single_backends: Single-port backends to merge in, routed by SNI.

        Returns:
            Self: The instantiated HAProxyRouteTcpFrontend class.
        """
        with_tls_terminate, without_tls_terminate, relation_ids_with_invalid_data = (
            cls._partition_routable_single_backends(single_backends)
        )
        # The port-range backend fixes the frontend's TLS termination mode;
        # single-port backends that don't match it cannot be merged in.
        if range_backend.application_data.tls_terminate:
            routable_singles = with_tls_terminate
            relation_ids_with_invalid_data.update(
                backend.relation_id for backend in without_tls_terminate
            )
        else:
            routable_singles = without_tls_terminate
            relation_ids_with_invalid_data.update(
                backend.relation_id for backend in with_tls_terminate
            )

        return cls(
            port_range=range_backend.application_data.port_range,
            backends=[range_backend, *routable_singles],
            # The port-range backend is the catch-all default; merged single-port
            # backends are routed by SNI on top of it.
            default_backend=range_backend,
            enforce_tls=range_backend.application_data.enforce_tls,
            tls_terminate=range_backend.application_data.tls_terminate,
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
            if sni_match_rule := backend.sni_match_rule:
                sni_fetch_method = (
                    "ssl_fc_sni" if backend.application_data.tls_terminate else "req.ssl_sni"
                )
                acls.append(
                    BackendRoutingConfiguration(
                        acl=f"acl is_{backend.name} {sni_fetch_method} {sni_match_rule}",
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
        return f"haproxy_route_tcp_{self.bind_port}_default_backend"

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
    def port(self) -> int:
        """Get the start port of this frontend.

        Returns:
            int: The start port.
        """
        return self.port_range.start

    @property
    def covered_ports(self) -> list[int]:
        """Get all individual ports covered by this frontend's port range.

        Returns:
            list[int]: List of ports from start to end (inclusive).
        """
        return list(range(self.port_range.start, self.port_range.end + 1))

    @property
    def bind_port(self) -> str:
        """Get the frontend bind port configuration.

        If the frontend is exposing a single port, return that port as an integer.
        If the frontend is exposing a port range, return the range in "start-end" format.

        Returns:
            str: The bind port configuration for the frontend.
        """
        if self.port_range.start == self.port_range.end:
            return str(self.port_range.start)
        return f"{self.port_range.start}-{self.port_range.end}"
