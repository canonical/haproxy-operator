#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-spoe-auth-operator charm file."""

import logging
import typing

import ops

from spoe_auth_service import (
    SpoeAuthService,
    SpoeAuthServiceConfigError,
    SpoeAuthServiceInstallError,
)
from state.charm_state import CharmState, InvalidCharmConfigError, ProxyMode
from state.exception import CharmStateValidationBaseError
from state.oauth import OAuthInformation

logger = logging.getLogger(__name__)

OAUTH_RELATION = "oauth"


class HaproxySpoeAuthCharm(ops.CharmBase):
    """Charm haproxy-spoe-auth."""

    def __init__(self, *args: typing.Any):
        """Initialize the charm and register event handlers.

        Args:
            args: Arguments to pass to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.service = SpoeAuthService()

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(
            self.on[OAUTH_RELATION].relation_changed, self._on_oauth_relation_changed
        )
        self.framework.observe(
            self.on[OAUTH_RELATION].relation_broken, self._on_oauth_relation_broken
        )

    def _on_install(self, _event: ops.InstallEvent) -> None:
        """Handle install event.

        Args:
            _event: The install event.
        """
        try:
            self.service.install()
            self.unit.status = ops.MaintenanceStatus("Service installed")
        except SpoeAuthServiceInstallError as exc:
            logger.exception("Failed to install service")
            self.unit.status = ops.BlockedStatus(f"Installation failed: {exc}")
            return

        self._reconcile()

    def _on_config_changed(self, _event: ops.ConfigChangedEvent) -> None:
        """Handle config changed event.

        Args:
            _event: The config changed event.
        """
        self._reconcile()

    def _on_oauth_relation_changed(self, _event: ops.RelationChangedEvent) -> None:
        """Handle oauth relation changed event.

        Args:
            _event: The relation changed event.
        """
        self._reconcile()

    def _on_oauth_relation_broken(self, _event: ops.RelationBrokenEvent) -> None:
        """Handle oauth relation broken event.

        Args:
            _event: The relation broken event.
        """
        self._reconcile()

    def _reconcile(self) -> None:
        """Reconcile the charm state and service configuration."""
        try:
            charm_state = self._get_charm_state()
            oauth_info = OAuthInformation.from_charm(self)

            self.service.reconcile(charm_state, oauth_info)

            if charm_state.mode == ProxyMode.OAUTH:
                self.unit.status = ops.ActiveStatus("OAuth authentication enabled")
            else:
                self.unit.status = ops.ActiveStatus("Service running without authentication")

        except CharmStateValidationBaseError as exc:
            logger.exception("Charm state validation failed")
            self.unit.status = ops.BlockedStatus(f"Configuration error: {exc}")
        except SpoeAuthServiceConfigError as exc:
            logger.exception("Service configuration failed")
            self.unit.status = ops.BlockedStatus(f"Service configuration failed: {exc}")
        except Exception as exc:
            logger.exception("Unexpected error during reconciliation")
            self.unit.status = ops.BlockedStatus(f"Unexpected error: {exc}")

    def _get_charm_state(self) -> CharmState:
        """Get the current charm state.

        Returns:
            CharmState: The current charm state.

        Raises:
            InvalidCharmConfigError: When the charm configuration is invalid.
        """
        try:
            oauth_relation = self.model.get_relation(OAUTH_RELATION)
            mode = ProxyMode.OAUTH if oauth_relation else ProxyMode.NOAUTH

            spoe_address = self.config.get("spoe-address", "127.0.0.1:3000")

            return CharmState(mode=mode, spoe_address=spoe_address)
        except Exception as exc:
            raise InvalidCharmConfigError(f"Invalid charm configuration: {exc}") from exc


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxySpoeAuthCharm)
