# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy service module."""

import logging

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import systemd

APT_PACKAGE_VERSION = "2.8.5-1ubuntu3"
APT_PACKAGE_NAME = "haproxy"
HAPROXY_SERVICE = "haproxy"

logger = logging.getLogger()


class HaproxyServiceStartError(Exception):
    """Error when starting the haproxy service."""


class HAProxyService:
    """HAProxy service class."""

    def install(self) -> None:
        """Install the haproxy apt package.

        Raises:
            RuntimeError: If the service is not running after installation.
        """
        apt.update()
        apt.add_package(package_names=APT_PACKAGE_NAME, version=APT_PACKAGE_VERSION)
        self.restart_haproxy_service()

        if not self.is_active():
            raise RuntimeError("HAProxy service is not running.")

    def restart_haproxy_service(self) -> None:
        """Restart the haporxy service."""
        systemd.service_restart(HAPROXY_SERVICE)

    def is_active(self) -> bool:
        """Indicate if the haproxy service is active.

        Returns:
            True if the haproxy is running.
        """
        return systemd.service_running(APT_PACKAGE_NAME)
