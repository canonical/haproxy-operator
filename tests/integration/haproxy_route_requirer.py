# pylint: disable=import-error
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import pathlib

import apt  # type: ignore
import ops
from any_charm_base import AnyCharmBase  # type: ignore
from haproxy_route import HaproxyRouteRequirer, RateLimitPolicy  # type: ignore

HAPROXY_ROUTE_RELATION = "require-haproxy-route"


class AnyCharm(AnyCharmBase):
    """haproxy-route requirer charm."""

    def __init__(self, *args, **kwargs):
        """Initialize the requirer charm."""  # noqa
        super().__init__(*args, **kwargs)
        self._haproxy_route = HaproxyRouteRequirer(self, HAPROXY_ROUTE_RELATION)

    def start_server(self):
        """Start apache2 webserver."""
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "ok"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")
        self.unit.status = ops.ActiveStatus("Server ready")

    def update_relation(self):
        """Update relation details for haproxy-route."""
        self._haproxy_route.provide_haproxy_route_requirements(
            service="any",
            ports=[80],
            subdomains=["ok", "ok2"],
            rate_limit_connections_per_minute=1,
            rate_limit_policy=RateLimitPolicy.DENY,
            check_interval=600,
            check_rise=3,
            check_fall=3,
            check_path="/ok",
            path_rewrite_expressions=["/ok"],
            deny_paths=["/private"],
        )
