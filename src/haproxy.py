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
        self.enable_haproxy_service()

        if not self.is_active():
            raise RuntimeError("HAProxy service is not running.")

    def enable_haproxy_service(self) -> None:
        """Enable and start the haporxy service if it is not running.

        Raises:
            HaproxyServiceStartError: If the haproxy service cannot be enabled and started.
        """
        try:
            systemd.service_enable(HAPROXY_SERVICE)
            if not systemd.service_running(HAPROXY_SERVICE):
                systemd.service_start(HAPROXY_SERVICE)
        except systemd.SystemdError as exc:
            logger.exception("Error starting the haproxy service")
            raise HaproxyServiceStartError("Error starting the haproxy service") from exc

    def is_active(self) -> bool:
        """Indicate if the haproxy service is active.

        Returns:
            True if the haproxy is running.
        """
        return systemd.service_running(APT_PACKAGE_NAME)
