#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""haproxy-operator charm file."""

import logging
import typing

import ops

from haproxy import HAProxyService

logger = logging.getLogger(__name__)


class HAProxyCharm(ops.CharmBase):
    """Charm haproxy."""

    def __init__(self, *args: typing.Any):
        """Initialize the charm and register event handlers.

        Args:
            args: Arguments to initialize the charm base.
        """
        super().__init__(*args)
        self.haproxy_service = HAProxyService()
        self.framework.observe(self.on.install, self._on_install)

    def _on_install(self, _: typing.Any) -> None:
        """Install the haproxy package.

        Raises:
            RuntimeError: When the haproxy service is not running after install.
        """
        self.haproxy_service.install()
        if not self.haproxy_service.is_active:
            logger.error("HAProxy service is not running.")
            raise RuntimeError("Service not running.")
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(HAProxyCharm)
