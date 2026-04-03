#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route-policy-operator charm."""

import logging
from typing import Any

import ops
from charmlibs.snap import SnapError
from charms.data_platform_libs.v0.data_interfaces import (
    DatabaseRequires,
)

from policy import (
    HaproxyRoutePolicyDatabaseMigrationError,
    configure_snap,
    install_snap,
    run_migrations,
    start_gunicorn_service,
)
from state.database import (
    DatabaseInformation,
    DatabaseRelationMissingError,
    DatabaseRelationNotReadyError,
)

logger = logging.getLogger(__name__)

DATABASE_RELATION = "database"
HAPROXY_ROUTE_POLICY_PORT = 8080


class HaproxyRoutePolicyCharm(ops.CharmBase):
    """Charm for HAProxy Route Policy service."""

    def __init__(self, *args: Any):
        super().__init__(*args)

        self.framework.observe(self.on.install, self._reconcile)
        self.framework.observe(self.on.upgrade_charm, self._reconcile)
        self.framework.observe(self.on.start, self._reconcile)
        self.framework.observe(self.on.config_changed, self._reconcile)

        self.database = DatabaseRequires(
            self,
            relation_name=DATABASE_RELATION,
            database_name=self.app.name,
            extra_user_roles="SUPERUSER",
        )
        self.framework.observe(self.database.on.database_created, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile snap configuration and service state."""
        try:
            install_snap()
            self.unit.status = ops.MaintenanceStatus("configuring haproxy-route-policy")
            database_information = DatabaseInformation.from_requirer(self, self.database)
            configure_snap(database_information.haproxy_route_policy_snap_configuration)
            self.unit.status = ops.MaintenanceStatus("running database migrations")
            run_migrations()
            self.unit.status = ops.MaintenanceStatus("starting gunicorn service")
            start_gunicorn_service()
            self.unit.open_port("tcp", HAPROXY_ROUTE_POLICY_PORT)
        except (SnapError, HaproxyRoutePolicyDatabaseMigrationError) as exc:
            logger.exception("Failed to reconcile haproxy-route-policy service")
            self.unit.status = ops.BlockedStatus(f"reconciliation failed: {exc}")
            return
        except DatabaseRelationMissingError:
            self.unit.status = ops.BlockedStatus("Missing database relation.")
            return
        except DatabaseRelationNotReadyError:
            logger.exception("Database relation not ready")
            self.unit.status = ops.WaitingStatus("waiting for complete database relation.")
            return

        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxyRoutePolicyCharm)
