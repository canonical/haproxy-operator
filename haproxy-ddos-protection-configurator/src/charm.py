#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""HAProxy DDoS protection configurator charm."""

import logging

import ops
from charms.haproxy.v0.ddos_protection import (
    DDOS_PROTECTION_RELATION_NAME,
    DDoSProtectionProviderAppData,
)
from pydantic import ValidationError

from state import CharmState, InvalidDDoSProtectionConfigError

logger = logging.getLogger()


class HAProxyDDoSProtectionConfiguratorCharm(ops.CharmBase):
    """Charm the HAProxy DDoS protection configurator."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        framework.observe(self.on.start, self._reconcile)
        framework.observe(self.on.config_changed, self._reconcile)
        framework.observe(
            self.on[DDOS_PROTECTION_RELATION_NAME].relation_created,
            self._reconcile,
        )

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state."""
        if not self.unit.is_leader():
            logger.info("Unit is not the leader, skipping relation data publication")
            self.unit.status = ops.ActiveStatus()
            return

        try:
            state = CharmState.from_charm(self)

            provider_data = DDoSProtectionProviderAppData(
                rate_limit_requests_per_minute=state.rate_limit_requests_per_minute,
                rate_limit_connections_per_minute=state.rate_limit_connections_per_minute,
                concurrent_connections_limit=state.concurrent_connections_limit,
                error_rate=state.error_rate_per_minute,
                # CharmState keeps the raw config strings so that pydantic can parse
                # them, including an optional status code for the deny policy.
                limit_policy_http=state.limit_policy_http,  # type: ignore[arg-type]
                limit_policy_tcp=state.limit_policy_tcp,  # type: ignore[arg-type]
                ip_allow_list=state.ip_allow_list,
                http_request_timeout=state.http_request_timeout,
                http_keepalive_timeout=state.http_keepalive_timeout,
                client_timeout=state.client_timeout,
                deny_paths=state.deny_paths,
            )
        except (InvalidDDoSProtectionConfigError, ValidationError) as e:
            logger.error("Failed to apply configuration: %s", str(e))
            self.unit.status = ops.BlockedStatus(str(e))
            return

        relations = self.model.relations.get(DDOS_PROTECTION_RELATION_NAME, [])
        published = 0
        failed_relation_ids: list[int | None] = []
        for relation in relations:
            try:
                relation.save(provider_data, self.app)
                published += 1
            except ops.ModelError as e:
                failed_relation_ids.append(relation.id)
                logger.error("Failed to publish configuration to relation %s: %s", relation.id, e)

        if failed_relation_ids:
            logger.warning(
                "Published DDoS protection configuration to %d/%d relations. "
                "Failed relation ids: %s",
                published,
                len(relations),
                failed_relation_ids,
            )
            self.unit.status = ops.ActiveStatus(f"{published}/{len(relations)} relation published")
            return

        logger.info("Configuration applied successfully")
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(HAProxyDDoSProtectionConfiguratorCharm)
