#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy DDoS protection configurator charm."""

import ops


class HAProxyDDoSProtectionConfiguratorCharm(ops.CharmBase):
    """Charm the HAProxy DDoS protection configurator."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        framework.observe(self.on.start, self._on_start)

    def _on_start(self, _: ops.EventBase) -> None:
        """Handle the start event."""
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(HAProxyDDoSProtectionConfiguratorCharm)
