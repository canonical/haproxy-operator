# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy service module."""

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import systemd

APT_PACKAGE_VERSION = "2.8.5-1ubuntu3"
APT_PACKAGE_NAME = "haproxy"


class HAProxyService:
    """HAProxy service class.

    Attrs:
       is_active: Indicate if the haproxy service is active and running.
    """

    def install(self) -> None:
        """Install the haproxy apt package."""
        apt.update()
        apt.add_package(package_names=APT_PACKAGE_NAME, version=APT_PACKAGE_VERSION)

    @property
    def is_active(self) -> bool:
        """Indicate if the haproxy service is active."""
        return systemd.service_running(APT_PACKAGE_NAME)
