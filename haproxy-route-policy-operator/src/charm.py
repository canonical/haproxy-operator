#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route-policy-operator charm."""

import json
import logging
from typing import Any

import ops
from charms.data_platform_libs.v0.data_interfaces import (
    DatabaseRequires,
)
from charms.haproxy_route_policy.v0.haproxy_route_policy import (
    HaproxyRoutePolicyProvider,
    HaproxyRoutePolicyRequirerAppData,
)

from policy import (
    HaproxyRoutePolicyClient,
    configure_snap,
    create_or_update_user,
    install_snap,
    run_migrations,
    start_gunicorn_service,
)
from state.database import (
    DatabaseInformation,
)
from state.policy import (
    DJANGO_ADMIN_CREDENTIALS_SECRET_LABEL,
    PEER_RELATION_NAME,
    HaproxyRoutePolicyInformation,
)
from state.validation import handle_charm_exceptions

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
        self.framework.observe(self.on.update_status, self._reconcile)
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

    @handle_charm_exceptions
    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile snap configuration and service state."""
        peer_relation = self.model.get_relation(PEER_RELATION_NAME)
        if not peer_relation:
            self.unit.status = ops.WaitingStatus("Waiting for peer relation.")
            return

        install_snap()
        self.unit.status = ops.MaintenanceStatus("configuring haproxy-route-policy")
        database_information = DatabaseInformation.from_requirer(self, self.database)
        haproxy_route_policy_information = HaproxyRoutePolicyInformation.from_charm(self)

        allowed_hosts = haproxy_route_policy_information.allowed_hosts_configuration
        haproxy_route_policy_requirer_data = None
        if relation := self.haproxy_route_policy.relation:
            haproxy_route_policy_requirer_data = relation.load(
                HaproxyRoutePolicyRequirerAppData, relation.app
            )

            if proxied_endpoint := haproxy_route_policy_requirer_data.proxied_endpoint:
                allowed_hosts.append(proxied_endpoint)

        configure_snap(
            {
                **{"allowed-hosts": json.dumps(allowed_hosts)},
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

        if haproxy_route_policy_requirer_data is not None:
            self._fetch_and_refresh_backend_requests(
                haproxy_route_policy_information, haproxy_route_policy_requirer_data
            )
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

    def _fetch_and_refresh_backend_requests(
        self,
        haproxy_route_policy_information: HaproxyRoutePolicyInformation,
        haproxy_route_policy_requirer_data: HaproxyRoutePolicyRequirerAppData,
    ) -> None:
        """Fetch backend requests from relation and refresh their status via the policy API."""
        backend_requests = haproxy_route_policy_requirer_data.backend_requests

        client = HaproxyRoutePolicyClient(
            username=haproxy_route_policy_information.admin_username,
            password=haproxy_route_policy_information.admin_password,
        )

        self.unit.status = ops.MaintenanceStatus("evaluating backend requests via policy service")
        evaluated = client.refresh(backend_requests)

        approved = [
            req
            for req, ev in zip(backend_requests, evaluated, strict=True)
            if ev.status == "accepted"
        ]
        self.haproxy_route_policy.set_approved_backend_requests(
            approved, HAPROXY_ROUTE_POLICY_PORT
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxyRoutePolicyCharm)
