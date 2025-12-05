# pylint: disable=import-error,duplicate-code,wrong-import-position
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import sys
from typing import Any

# The last one is the dynamic modules. That way we get the new cryptography
# library, not the system one.
sys.path.insert(0, sys.path[-1])

import pathlib
import apt
import ops
from any_charm_base import AnyCharmBase
from haproxy_route import HaproxyRouteRequirer


HAPROXY_ROUTE_RELATION = "require-haproxy-route"

class AnyCharm(AnyCharmBase):
    """haproxy-route requirer charm."""

    def __init__(self, *args, **kwargs):
        """Initialize the requirer charm."""
        super().__init__(*args, **kwargs)
        self._haproxy_route = HaproxyRouteRequirer(self, HAPROXY_ROUTE_RELATION)

    def start_server(self, hostname):
        """Start apache2 webserver."""
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "index.html"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text(f"ok!\n{self.app.name}\n{hostname}")
        self.unit.status = ops.ActiveStatus("Server ready")

    def update_relation(self, haproxy_route_params: dict[str, Any]):
        """Update relation details for haproxy-route.

        Args:
          haproxy_route_params: arguments to pass relation.
        """
        self.start_server(haproxy_route_params.get('hostname'))
        self._haproxy_route.provide_haproxy_route_requirements(**haproxy_route_params)
