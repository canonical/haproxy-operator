#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""haproxy-operator charm file."""

import logging
import typing

import ops

from haproxy import HAProxyService
from state.config import CharmConfig
from state.validation import validate_config_and_integration

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
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_install(self, _: typing.Any) -> None:
        """Install the haproxy package."""
        self.haproxy_service.install()
        self.unit.status = ops.ActiveStatus()

    @validate_config_and_integration(defer=False)
    def _on_config_changed(self, _: typing.Any) -> None:
        """Handle the config-changed event."""
        config = CharmConfig.from_charm(self)
        self.haproxy_service.reconcile(config)
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(HAProxyCharm)
