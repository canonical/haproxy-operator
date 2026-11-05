# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""The keepalived service module."""

import logging
import shutil

from charms.operator_libs_linux.v0 import apt

APT_PACKAGE_NAME = "keepalived"

logger = logging.getLogger(__name__)


def keepalived_to_install() -> str | None:
    """Return the apt package needed to install keepalived.

    Returns:
        str | None: The package to install, or None if keepalived is present.
    """
    if not shutil.which(APT_PACKAGE_NAME):
        return APT_PACKAGE_NAME
    return None


class KeepalivedService:
    """Keepalived service class."""

    def install(self) -> None:
        """Install the keepalived apt package."""
        if package := keepalived_to_install():
            logger.info("Installing keepalived package: %s", package)
            apt.add_package(package_names=[package], update_cache=True)
