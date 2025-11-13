#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-spoe-auth-operator charm file."""

import logging
import typing

import ops
from haproxy_spoe_auth_operator.src.haproxy_spoe_auth_service import (
    SpoeAuthService,
    SpoeAuthServiceConfigError,
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

        # OAuth requirer will be added here once the library is fetched
        # Example: self.oauth = OAuthRequirer(self, relation_name=OAUTH_RELATION)

        self.framework.observe(self.on.install, self._reconcile)
        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(
            self.on[OAUTH_RELATION].relation_changed, self._reconcile
        )
        self.framework.observe(
            self.on[OAUTH_RELATION].relation_broken, self._reconcile
        )


    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state and service configuration."""
        try:
            charm_state = self._get_charm_state()
            oauth_info = OAuthInformation.from_charm(self)

            self.service.reconcile(charm_state, oauth_info)

        except CharmStateValidationBaseError as exc:
            logger.exception("Charm state validation failed")
            self.unit.status = ops.BlockedStatus(f"Configuration error: {exc}")
        except SpoeAuthServiceConfigError as exc:
            logger.exception("Service configuration failed")
            self.unit.status = ops.BlockedStatus(f"Service configuration failed: {exc}")
        except Exception as exc:
            logger.exception("Unexpected error during reconciliation")
            self.unit.status = ops.BlockedStatus(f"Unexpected error: {exc}")


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxySpoeAuthCharm)
