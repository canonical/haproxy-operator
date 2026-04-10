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
from charms.haproxy_route_policy.v0.haproxy_route_policy import (
    HaproxyRoutePolicyProvider,
    HaproxyRoutePolicyRequirerAppData,
)
from pydantic import ValidationError

from policy import (
    HaproxyRoutePolicyDatabaseMigrationError,
    configure_snap,
    create_or_update_user,
    install_snap,
    run_migrations,
    start_gunicorn_service,
)
from state.database import (
    DatabaseInformation,
    DatabaseRelationMissingError,
    DatabaseRelationNotReadyError,
)
from state.policy import (
    DJANGO_ADMIN_CREDENTIALS_SECRET_LABEL,
    PEER_RELATION_NAME,
    DjangoAdminCredentialsInvalidError,
    DjangoAdminCredentialsMissingError,
    DjangoSecretKeyMissingError,
    HaproxyRoutePolicyInformation,
    PeerRelationMissingError,
)

logger = logging.getLogger(__name__)

DATABASE_RELATION = "database"
HAPROXY_ROUTE_POLICY_PORT = 8080
HAPROXY_ROUTE_POLICY_RELATION_NAME = "haproxy-route-policy"


class HaproxyRoutePolicyCharm(ops.CharmBase):
    """Charm for HAProxy Route Policy service."""

    def __init__(self, *args: Any):
        super().__init__(*args)

        self.framework.observe(self.on.install, self._reconcile)
        self.framework.observe(self.on.upgrade_charm, self._reconcile)
        self.framework.observe(self.on.start, self._reconcile)
        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(
            self.on.get_admin_credentials_action, self._on_get_admin_credentials_action
        )
        self.framework.observe(self.on[PEER_RELATION_NAME].relation_joined, self._reconcile)
        self.framework.observe(self.on[PEER_RELATION_NAME].relation_changed, self._reconcile)

        self.database = DatabaseRequires(
            self,
            relation_name=DATABASE_RELATION,
            database_name=self.app.name,
            extra_user_roles="SUPERUSER",
        )
        self.framework.observe(self.database.on.database_created, self._reconcile)

        self.haproxy_route_policy = HaproxyRoutePolicyProvider(
            self, HAPROXY_ROUTE_POLICY_RELATION_NAME
        )
        self.framework.observe(
            self.on[self.haproxy_route_policy.relation_name].relation_created, self._reconcile
        )
        self.framework.observe(
            self.on[self.haproxy_route_policy.relation_name].relation_changed, self._reconcile
        )
        self.framework.observe(
            self.on[self.haproxy_route_policy.relation_name].relation_broken, self._reconcile
        )
        self.framework.observe(
            self.on[self.haproxy_route_policy.relation_name].relation_departed, self._reconcile
        )

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile snap configuration and service state."""
        try:
            install_snap()
            self.unit.status = ops.MaintenanceStatus("configuring haproxy-route-policy")
            database_information = DatabaseInformation.from_requirer(self, self.database)
            haproxy_route_policy_information = HaproxyRoutePolicyInformation.from_charm(self)
            configure_snap(
                {
                    **haproxy_route_policy_information.allowed_hosts_snap_configuration,
                    **database_information.haproxy_route_policy_snap_configuration,
                }
            )

            if self.unit.is_leader():
                self.unit.status = ops.MaintenanceStatus("[leader] running database migrations")
                run_migrations()

                self.unit.status = ops.MaintenanceStatus("[leader] updating Django admin user")
                create_or_update_user(
                    haproxy_route_policy_information.admin_username,
                    haproxy_route_policy_information.admin_password,
                )

            self.unit.status = ops.MaintenanceStatus("starting gunicorn service")
            start_gunicorn_service()

            self.unit.open_port("tcp", HAPROXY_ROUTE_POLICY_PORT)

            if relation := self.haproxy_route_policy.relation:
                requests = relation.load(
                    HaproxyRoutePolicyRequirerAppData, relation.app
                ).backend_requests
                logger.info(f"backend requests {requests}, auto approved.")
                self.haproxy_route_policy.set_approved_backend_requests(requests)

        except DatabaseRelationMissingError:
            self.unit.status = ops.BlockedStatus("Missing database relation.")
            return
        except DatabaseRelationNotReadyError:
            logger.exception("Database relation not ready")
            self.unit.status = ops.WaitingStatus("waiting for complete database relation.")
            return
        except PeerRelationMissingError:
            logger.exception("Peer relation missing")
            self.unit.status = ops.WaitingStatus("Waiting for peer relation.")
            return
        except (
            DjangoSecretKeyMissingError,
            DjangoAdminCredentialsMissingError,
            DjangoAdminCredentialsInvalidError,
        ):
            logger.exception("Django shared configuration not ready")
            self.unit.status = ops.WaitingStatus(
                "Waiting for complete shared configuration from leader."
            )
            return
        except (SnapError, HaproxyRoutePolicyDatabaseMigrationError) as exc:
            logger.exception("Failed to reconcile haproxy-route-policy service")
            self.unit.status = ops.BlockedStatus(f"reconciliation failed: {exc}")
            return
        except ValidationError:
            logger.exception("Invalid haproxy-route-policy relation data")
            self.unit.status = ops.WaitingStatus(
                "Waiting for valid haproxy-route-policy relation data"
            )
            return

        self.unit.status = ops.ActiveStatus()

    def _on_get_admin_credentials_action(self, event: ops.ActionEvent) -> None:
        """Handle the get-admin-credentials action."""
        try:
            secret = self.model.get_secret(
                label=DJANGO_ADMIN_CREDENTIALS_SECRET_LABEL
            ).get_content()
            event.set_results(
                {
                    "username": secret["username"],
                    "password": secret["password"],
                }
            )
            return
        except ops.SecretNotFoundError:
            event.fail("Admin credentials not found.")


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxyRoutePolicyCharm)
