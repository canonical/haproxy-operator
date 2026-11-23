# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""The keepalived service module."""

import json
import logging
import shutil

# We silence this rule because subprocess is only used to look up the network interface
# for the configured virtual IP.
import subprocess  # nosec B404
from pathlib import Path

from charmlibs import apt
from charms.operator_libs_linux.v1 import systemd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import IPvAnyInterface

APT_PACKAGE_NAME = "keepalived"
KEEPALIVED_SERVICE = "keepalived"
KEEPALIVED_CONFIG_DIR = Path("/etc/keepalived")
KEEPALIVED_CONFIG = KEEPALIVED_CONFIG_DIR / "keepalived.conf"
KEEPALIVED_CONFIG_TEMPLATE = "keepalived.conf.j2"

logger = logging.getLogger(__name__)


class KeepalivedConfigurationError(Exception):
    """Error when rendering or applying the keepalived configuration."""


def keepalived_to_install() -> str | None:
    """Return the apt package needed to install keepalived.

    Returns:
        str | None: The package to install, or None if keepalived is present.
    """
    if not shutil.which(APT_PACKAGE_NAME):
        return APT_PACKAGE_NAME
    return None


def get_network_interface(address: str) -> str:
    """Return the network interface used to reach the given address.

    Args:
        address: The address to look up.

    Raises:
        KeepalivedConfigurationError: When the interface cannot be determined.

    Returns:
        str: The name of the network interface.
    """
    ip_command = shutil.which("ip")
    if not ip_command:
        raise KeepalivedConfigurationError(
            "The 'ip' command is required to determine the network interface."
        )
    try:
        # We ignore bandit rule as we're not parsing user input.
        output = subprocess.check_output(  # nosec B603
            [ip_command, "-j", "route", "get", address],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise KeepalivedConfigurationError(
            f"Could not determine the network interface for the virtual IP {address}."
        ) from exc

    try:
        routes = json.loads(output)
    except json.JSONDecodeError as exc:
        raise KeepalivedConfigurationError(
            f"Could not parse the route lookup output for the virtual IP {address}."
        ) from exc

    if not routes or not routes[0].get("dev"):
        raise KeepalivedConfigurationError(
            f"Could not determine the network interface for the virtual IP {address}."
        )
    return routes[0]["dev"]


class KeepalivedService:
    """Keepalived service class.

    The package is intentionally not pinned with ``apt-mark hold`` so that
    unattended-upgrades can apply security updates. Unlike haproxy, keepalived
    does not need a pinned version to keep the charm-generated configuration
    compatible.
    """

    def install(self) -> None:
        """Install the keepalived apt package."""
        if package := keepalived_to_install():
            logger.info("Installing keepalived package: %s", package)
            apt.add_package(package_names=[package], update_cache=True)

    def reconcile(self, vip: IPvAnyInterface | None) -> None:
        """Apply the keepalived configuration for the given virtual IP.

        Keepalived is only started when a virtual IP is configured. When the
        option is unset, the generated configuration is removed and the service
        is stopped.

        Args:
            vip: The configured virtual IP address, or None when unset.
        """
        if vip is None:
            self._stop()
            return

        address = str(vip.ip)
        interface = get_network_interface(address)
        changed = self._write_config(self._render_config(vip, interface))
        if not systemd.service_running(KEEPALIVED_SERVICE):
            logger.info("Starting keepalived for virtual IP %s.", vip)
            systemd.service_start(KEEPALIVED_SERVICE)
        elif changed:
            logger.info("Reloading keepalived for virtual IP %s.", vip)
            systemd.service_reload(KEEPALIVED_SERVICE)

    def _render_config(self, vip: IPvAnyInterface, interface: str) -> str:
        """Render the keepalived configuration.

        Args:
            vip: The virtual IP address to configure.
            interface: The network interface on which to configure the virtual IP.

        Returns:
            str: The rendered keepalived configuration.
        """
        env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return env.get_template(KEEPALIVED_CONFIG_TEMPLATE).render(vip=vip, interface=interface)

    def _write_config(self, config: str) -> bool:
        """Write the keepalived configuration if it changed.

        Args:
            config: The rendered keepalived configuration.

        Returns:
            bool: Whether the configuration changed.
        """
        KEEPALIVED_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if KEEPALIVED_CONFIG.exists() and KEEPALIVED_CONFIG.read_text() == config:
            return False
        KEEPALIVED_CONFIG.write_text(config)
        KEEPALIVED_CONFIG.chmod(0o644)
        return True

    def _stop(self) -> None:
        """Stop keepalived and remove its configuration."""
        KEEPALIVED_CONFIG.unlink(missing_ok=True)
        if systemd.service_running(KEEPALIVED_SERVICE):
            logger.info("Stopping keepalived because no virtual IP is configured.")
            systemd.service_stop(KEEPALIVED_SERVICE)
