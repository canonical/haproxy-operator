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

        self._render_file(HAPROXY_DHCONFIG, HAPROXY_DH_PARAM, 0o644)
        self._restart_haproxy_service()

        if not self.is_active():
            raise RuntimeError("HAProxy service is not running.")

    def reconcile(self) -> None:
        """Render the haproxy config and restart the haproxy service."""
        self._render_haproxy_config()
        self._restart_haproxy_service()

    def _restart_haproxy_service(self) -> None:
        """Restart the haporxy service."""
        systemd.service_restart(HAPROXY_SERVICE)

    def is_active(self) -> bool:
        """Indicate if the haproxy service is active.

        Returns:
            True if the haproxy is running.
        """
        return systemd.service_running(APT_PACKAGE_NAME)

    def _render_file(self, path: Path, content: str, mode: int) -> None:
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

    def _render_haproxy_config(self) -> None:
        """Render the haproxy configuration file."""
        with open("templates/haproxy.cfg.j2", "r", encoding="utf-8") as file:
            template = Template(file.read(), keep_trailing_newline=True)
        rendered = template.render()
        self._render_file(HAPROXY_CONFIG, rendered, 0o644)
