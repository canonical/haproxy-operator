# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy service module."""

import logging
import os
import pwd
from pathlib import Path

from charms.operator_libs_linux.v0 import apt
from charms.operator_libs_linux.v1 import systemd
from jinja2 import Template

from legacy import generate_service_config
from state.config import CharmConfig
from state.ingress import IngressRequirersInformation

APT_PACKAGE_VERSION = "2.8.5-1ubuntu3"
APT_PACKAGE_NAME = "haproxy"
HAPROXY_CONFIG_DIR = Path("/etc/haproxy")
HAPROXY_CONFIG = Path(HAPROXY_CONFIG_DIR / "haproxy.cfg")
HAPROXY_USER = "haproxy"
# Configuration used to parameterize Diffie-Hellman key exchange.
# The base64 content of the file is hard-coded here to avoid having to fetch
# the file from https://ssl-config.mozilla.org/ffdhe2048.txt as suggested by Mozilla.
# As the size is 2048, it's safe to use the standard FFDHE parameters.
# They are more compatible, and there aren't concerns about their security.
HAPROXY_DH_PARAM = (
    "-----BEGIN DH PARAMETERS-----\n"
    "MIIBCAKCAQEA//////////+t+FRYortKmq/cViAnPTzx2LnFg84tNpWp4TZBFGQz\n"
    "+8yTnc4kmz75fS/jY2MMddj2gbICrsRhetPfHtXV/WVhJDP1H18GbtCFY2VVPe0a\n"
    "87VXE15/V8k1mE8McODmi3fipona8+/och3xWKE2rec1MKzKT0g6eXq8CrGCsyT7\n"
    "YdEIqUuyyOP7uWrat2DX9GgdT0Kj3jlN9K5W7edjcrsZCwenyO4KbXCeAvzhzffi\n"
    "7MA0BM0oNC9hkXL+nOmFg/+OTxIy7vKBg8P+OxtMb61zO7X8vC7CIAXFjvGDfRaD\n"
    "ssbzSibBsu/6iGtCOGEoXJf//////////wIBAg==\n"
    "-----END DH PARAMETERS-----"
)
HAPROXY_DHCONFIG = Path(HAPROXY_CONFIG_DIR / "ffdhe2048.txt")
HAPROXY_SERVICE = "haproxy"


logger = logging.getLogger()


class HaproxyServiceRestartError(Exception):
    """Error when restarting the haproxy service."""


class HAProxyService:
    """HAProxy service class."""

    def install(self) -> None:
        """Install the haproxy apt package.

        Raises:
            RuntimeError: If the service is not running after installation.
        """
        apt.update()
        apt.add_package(package_names=APT_PACKAGE_NAME, version=APT_PACKAGE_VERSION)

        render_file(HAPROXY_DHCONFIG, HAPROXY_DH_PARAM, 0o644)
        self._restart_haproxy_service()

        if not self.is_active():
            raise RuntimeError("HAProxy service is not running.")

    def reconcile(
        self,
        config: CharmConfig,
        services_dict: dict,
        ingress_requirers_information: IngressRequirersInformation,
    ) -> None:
        """Render the haproxy config and restart the haproxy service.

        Args:
            config: charm config
            services_dict: The parsed services dict for reverseproxy.
            ingress_requirers_information: Information about ingress requirers.
        """
        # At this point, the charm should already verify that
        # only one relation is established
        if services_dict and ingress_requirers_information.backends:
            raise AssertionError

        self._render_haproxy_config(config, services_dict, ingress_requirers_information)
        self._restart_haproxy_service()

    def is_active(self) -> bool:
        """Indicate if the haproxy service is active.

        Returns:
            True if the haproxy is running.
        """
        return systemd.service_running(APT_PACKAGE_NAME)

    def _render_haproxy_config(
        self,
        config: CharmConfig,
        services_dict: dict,
        ingress_requirers_information: IngressRequirersInformation,
    ) -> None:
        """Render the haproxy configuration file.

        Args:
            config: charm config
            services_dict: The parsed services dict for reverseproxy.
            ingress_requirers_information: Information about ingress requirers.
        """
        with open("templates/haproxy.cfg.j2", "r", encoding="utf-8") as file:
            template = Template(
                file.read(), keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True
            )

        rendered = template.render(
            config_global_max_connection=config.global_max_connection,
            services=generate_service_config(config.haproxy_frontend_prefix, services_dict),
            ingress_requirers_information=ingress_requirers_information,
        )
        render_file(HAPROXY_CONFIG, rendered, 0o644)
        self._restart_haproxy_service()

    def _restart_haproxy_service(self) -> None:
        """Restart the haporxy service."""
        systemd._systemctl("reset-failed", HAPROXY_SERVICE)  # pylint: disable=protected-access
        systemd.service_restart(HAPROXY_SERVICE)


def render_file(path: Path, content: str, mode: int) -> None:
    """Write a content rendered from a template to a file.

    Args:
        path: Path object to the file.
        content: the data to be written to the file.
        mode: access permission mask applied to the
            file using chmod (e.g. 0o640).
    """
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)
    u = pwd.getpwnam(HAPROXY_USER)
    # Set the correct ownership for the file.
    os.chown(path, uid=u.pw_uid, gid=u.pw_gid)
