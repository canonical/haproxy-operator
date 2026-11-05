# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""The keepalived service module."""

import logging
import shutil

from charms.operator_libs_linux.v0 import apt

APT_PACKAGE_NAME = "keepalived"

logger = logging.getLogger(__name__)


def keepalived_to_install() -> list[str]:
    """Return the apt packages needed to install keepalived.

    Returns:
        list[str]: The packages to install, or an empty list if keepalived is present.
    """
    if not shutil.which(APT_PACKAGE_NAME):
        return [APT_PACKAGE_NAME]
    return []


class KeepalivedService:
    """Keepalived service class."""

    def install(self) -> None:
        """Install the keepalived apt package."""
        if packages := keepalived_to_install():
            logger.info("Installing keepalived packages: %s", packages)
            apt.add_package(package_names=packages, update_cache=True)
