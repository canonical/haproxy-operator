#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route-policy-operator charm."""

from __future__ import annotations

import json
import logging
import secrets
import subprocess
from typing import Any

import ops
from charmlibs import snap as snap_lib

import snap

logger = logging.getLogger(__name__)

POSTGRESQL_RELATION = "postgresql"
VALID_LOG_LEVELS = {"debug", "info", "warning", "error", "critical"}


class HaproxyRoutePolicyCharm(ops.CharmBase):
    """Charm for HAProxy Route Policy service."""

    _stored = ops.StoredState()

    def __init__(self, *args: Any):
        super().__init__(*args)
        self._stored.set_default(secret_key="")

        self.framework.observe(self.on.install, self._install)
        self.framework.observe(self.on.upgrade_charm, self._install)
        self.framework.observe(self.on.start, self._reconcile)
        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(self.on[POSTGRESQL_RELATION].relation_joined, self._reconcile)
        self.framework.observe(self.on[POSTGRESQL_RELATION].relation_changed, self._reconcile)
        self.framework.observe(self.on[POSTGRESQL_RELATION].relation_broken, self._reconcile)

        self.unit.open_port("tcp", 8080)

    def _install(self, _: ops.EventBase) -> None:
        """Install the route-policy snap."""
        channel = str(self.model.config["snap-channel"])
        self.unit.status = ops.MaintenanceStatus("installing haproxy-route-policy snap")
        try:
            snap.install_snap(channel=channel)
        except snap_lib.SnapError as exc:
            logger.exception("Failed to install haproxy-route-policy snap")
            self.unit.status = ops.BlockedStatus(f"snap installation failed: {exc}")
            return
        self._reconcile(_)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile snap configuration and service state."""
        credentials = self._get_postgresql_credentials()
        if not credentials:
            self.unit.status = ops.WaitingStatus("waiting for postgresql relation data")
            return

        try:
            snap_config = {
                "secret-key": self._get_secret_key(),
                "debug": bool(self.model.config["debug"]),
                "allowed-hosts": self._validated_allowed_hosts(),
                "log-level": self._validated_log_level(),
                **credentials,
            }
            self.unit.status = ops.MaintenanceStatus("configuring haproxy-route-policy")
            snap.configure_snap(snap_config)
            self.unit.status = ops.MaintenanceStatus("running database migrations")
            snap.run_migrations()
            self.unit.status = ops.MaintenanceStatus("starting gunicorn service")
            snap.start_gunicorn_service()
        except (ValueError, snap_lib.SnapError, subprocess.CalledProcessError) as exc:
            logger.exception("Failed to reconcile haproxy-route-policy service")
            self.unit.status = ops.BlockedStatus(f"reconciliation failed: {exc}")
            return

        self.unit.status = ops.ActiveStatus()

    def _get_secret_key(self) -> str:
        """Get a stable secret key for Django."""
        config_secret_key = str(self.model.config["secret-key"]).strip()
        if config_secret_key:
            return config_secret_key
        if self._stored.secret_key:
            return self._stored.secret_key
        self._stored.secret_key = secrets.token_urlsafe(48)
        return self._stored.secret_key

    def _validated_allowed_hosts(self) -> str:
        """Validate allowed-hosts config and return it in JSON string form."""
        raw_value = str(self.model.config["allowed-hosts"])
        parsed = json.loads(raw_value)
        if not isinstance(parsed, list) or not all(isinstance(host, str) for host in parsed):
            raise ValueError("allowed-hosts must be a JSON array of strings")
        return raw_value

    def _validated_log_level(self) -> str:
        """Validate log-level config."""
        log_level = str(self.model.config["log-level"]).lower()
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(f"log-level must be one of {', '.join(sorted(VALID_LOG_LEVELS))}")
        return log_level

    def _get_postgresql_credentials(self) -> dict[str, str] | None:
        """Read PostgreSQL credentials from relation databag."""
        relation = self.model.get_relation(POSTGRESQL_RELATION)
        if relation is None or relation.app is None:
            return None

        relation_data = relation.data[relation.app]
        endpoints = relation_data.get("endpoints")
        database = relation_data.get("database")
        username = relation_data.get("username")
        password = relation_data.get("password")

        if not all([endpoints, database, username, password]):
            return None

        endpoint = str(endpoints).split(",")[0].strip()
        host, _, port = endpoint.partition(":")
        if not port:
            port = "5432"

        return {
            "database-host": host,
            "database-port": port,
            "database-user": str(username),
            "database-password": str(password),
            "database-name": str(database),
        }


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxyRoutePolicyCharm)
