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
from pydantic import IPvAnyAddress, RootModel
from pydantic.dataclasses import dataclass


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
class HAProxyRouteTcpEndpoint(HaproxyRouteTcpRequirerData):
    """Represent an endpoint for haproxy-route-tcp.

    Attrs:
        consistent_hashing: Whether consistent hashing should be applied for this backend.
        servers: List of backend servers for this TCP endpoint.
        name: Unique name for this TCP endpoint.
        tcp_check_options: TCP health check options for HAProxy configuration.
    """

    @classmethod
    def from_haproxy_route_tcp_requirer_data(cls, provider: HaproxyRouteTcpRequirerData) -> "Self":
        """Instantiate a HAProxyRouteTcpEndpoint class from the parent class.

        Args:
            provider: parent class.

        Returns:
            Self: The instantiated HAProxyRouteTcpEndpoint class.
        """
        return cls(**RootModel[HaproxyRouteTcpRequirerData](provider).model_dump())

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
        for i, unit_data in enumerate(self.units_data):
            servers.append(
                HaproxyRouteTcpServer(
                    server_name=f"{self.application}-{i}",
                    port=cast(int, self.application_data.backend_port),
                    address=unit_data.address,
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
            if check.check_type is None:
                return []
            if check.check_type == TCPHealthCheckType.GENERIC:
                options = ["option tcp-check"]
                if send := self.application_data.check.send:
                    options.append(f"tcp-check send {repr(send)}")
                if expect := self.application_data.check.expect:
                    options.append(f"tcp-check expect string {repr(expect)}")
                return options
            if check.check_type in [TCPHealthCheckType.POSTGRES, TCPHealthCheckType.MYSQL]:
                db_user = f" {check.db_user}" if check.db_user else ""
                return [f"option {str(check.check_type)}{db_user}"]
            return [f"option {str(check.check_type)}"]
        return []
