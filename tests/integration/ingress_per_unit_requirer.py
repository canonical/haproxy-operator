# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code,import-error,too-few-public-methods

"""Ingress per unit requirer any charm."""
import pathlib

import apt
import ops
from any_charm_base import AnyCharmBase
from ingress_per_unit import IngressPerUnitReadyForUnitEvent, IngressPerUnitRequirer


class AnyCharm(AnyCharmBase):
    """Any charm that uses the ingress per unit requirer interface."""

    def __init__(self, *args, **kwargs):
        """Initialize the charm.

        Args:
            args: Positional arguments.
            kwargs: Keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.ingress_per_unit = IngressPerUnitRequirer(
            self, port=80, relation_name="require-ingress-per-unit", strip_prefix=True
        )
        self.framework.observe(self.on.install, self.start_server)
        self.framework.observe(self.ingress_per_unit.on.ready_for_unit, self._on_ingress_ready)

    def start_server(self, _: ops.InstallEvent):
        """Start the server."""
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "ok"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")

    def _on_ingress_ready(self, _: IngressPerUnitReadyForUnitEvent):
        """Relation changed handler."""
        self.unit.status = ops.ActiveStatus("Server Ready")
