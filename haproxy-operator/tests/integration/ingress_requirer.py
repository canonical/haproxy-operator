# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=import-error,too-few-public-methods

"""Ingress per app requirer any charm."""

import pathlib

import apt
import ops
from any_charm_base import AnyCharmBase
from ingress import IngressPerAppRequirer


class AnyCharm(AnyCharmBase):
    """Any charm that uses the ingress per app requirer interface."""

    def __init__(self, *args, **kwargs):
        """Initialize the charm."""
        super().__init__(*args, **kwargs)
        self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)

    def get_ingress_url(self):
        """Return the URL published by the ingress provider."""
        return self.ingress.url

    def start_server(self):
        """Install and start the test HTTP server."""
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "ok"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")
        self.unit.status = ops.ActiveStatus("Server ready")
