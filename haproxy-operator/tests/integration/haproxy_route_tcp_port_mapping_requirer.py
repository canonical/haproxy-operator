# pylint: disable=import-error
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route-tcp requirer source that exercises the port_mapping attribute."""

import logging

import ops

# Ignoring here to make the linter happy as these modules will be available
# only inside the anycharm unit.
from any_charm_base import AnyCharmBase  # type: ignore
from haproxy_route_tcp import HaproxyRouteTcpRequirer  # type: ignore

HAPROXY_ROUTE_TCP_RELATION = "require-haproxy-route-tcp"

logger = logging.getLogger()


class AnyCharm(AnyCharmBase):
    """haproxy-route-tcp requirer charm exercising port_mapping."""

    def __init__(self, *args, **kwargs):
        # We don't need to include *args and *kwargs in the docstring here.
        """Initialize the requirer charm."""
        super().__init__(*args, **kwargs)
        self._haproxy_route_tcp = HaproxyRouteTcpRequirer(self, HAPROXY_ROUTE_TCP_RELATION)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_config_changed(self, _: ops.EventBase):
        """Mark the unit as ready; no backend service is needed to render the config."""
        self.unit.status = ops.ActiveStatus("Ready.")

    def update_relation_with_port_mapping(self):
        """Provide a port-range to port-range mapping.

        Frontend ports 8080-8090 map to backend ports 9080-9090, i.e. a positive
        offset of 1000. HAProxy should bind the whole range and translate the
        destination port with `set-dst-port dst_port,add(1000)`.
        """
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port_mapping="8080-8090:9080-9090",
            enforce_tls=False,
            tls_terminate=False,
        )

    def update_relation_with_port_and_backend_port(self):
        """Provide a single-port mapping built from port and backend_port.

        Frontend port 8080 maps to backend port 9090, i.e. a positive offset of
        1010 translated with `set-dst-port dst_port,add(1010)`.
        """
        self._haproxy_route_tcp.provide_haproxy_route_tcp_requirements(
            port=8080,
            backend_port=9090,
            enforce_tls=False,
            tls_terminate=False,
        )
