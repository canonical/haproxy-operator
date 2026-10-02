#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy DDoS protection configurator charm."""

import logging

import ops
from charms.haproxy.v0.ddos_protection import (
    DDOS_PROTECTION_RELATION_NAME,
    DataValidationError,
    DDoSProtectionProvider,
)

from state import CharmState, InvalidDDoSProtectionConfigError

logger = logging.getLogger()


class HAProxyDDoSProtectionConfiguratorCharm(ops.CharmBase):
    """Charm the HAProxy DDoS protection configurator."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        self._ddos_provider = DDoSProtectionProvider(self)

        framework.observe(self.on.start, self._reconcile)
        framework.observe(self.on.config_changed, self._reconcile)
        framework.observe(
            self.on[DDOS_PROTECTION_RELATION_NAME].relation_created,
            self._reconcile,
        )

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state."""
        try:
            state = CharmState.from_charm(self)

            self._ddos_provider.set_config(
                rate_limit_requests_per_minute=state.rate_limit_requests_per_minute,
                rate_limit_connections_per_minute=state.rate_limit_connections_per_minute,
                concurrent_connections_limit=state.concurrent_connections_limit,
                error_rate=state.error_rate_per_minute,
                limit_policy_http=state.limit_policy_http,
                limit_policy_tcp=state.limit_policy_tcp,
                ip_allow_list=state.ip_allow_list,
                http_request_timeout=state.http_request_timeout,
                http_keepalive_timeout=state.http_keepalive_timeout,
                client_timeout=state.client_timeout,
                deny_paths=state.deny_paths,
            )

            logger.info("Configuration applied successfully")
            self.unit.status = ops.ActiveStatus()

        except (InvalidDDoSProtectionConfigError, DataValidationError) as e:
            logger.error("Failed to apply configuration: %s", str(e))
            self.unit.status = ops.BlockedStatus(str(e))


if __name__ == "__main__":  # pragma: nocover
    ops.main(HAProxyDDoSProtectionConfiguratorCharm)
