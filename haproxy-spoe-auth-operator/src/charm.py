#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-spoe-auth-operator charm file."""

import logging
import typing

import ops
from charms.haproxy.v0.spoe_auth import HaproxyEvent, SpoeAuthProvider
from charms.hydra.v0.oauth import ClientConfig, OAuthRequirer

from haproxy_spoe_auth_service import (
    COOKIE_NAME,
    OIDC_CALLBACK_PATH,
    OIDC_CALLBACK_PORT,
    SPOP_PORT,
    SpoeAuthService,
    SpoeAuthServiceConfigError,
)
from state import CharmState, InvalidCharmConfigError, OauthInformation

logger = logging.getLogger(__name__)

OAUTH_RELATION = "oauth"
OIDC_SCOPE = "openid email profile"
SPOE_AUTH_MESSAGE_NAME = "try-auth-oidc"
SPOE_AUTH_RELATION = "spoe-auth"
VAR_AUTHENTICATED_SCOPE = "sess"
VAR_AUTHENTICATED = "is_authenticated"
VAR_REDIRECT_URL_SCOPE = "sess"
VAR_REDIRECT_URL = "redirect_url"


class HaproxySpoeAuthCharm(ops.CharmBase):
    """Charm haproxy-spoe-auth."""

    def __init__(self, *args: typing.Any):
        """Initialize the charm and register event handlers.

        Args:
            args: Arguments to pass to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.service = SpoeAuthService()
        self._spoe_auth_provider = SpoeAuthProvider(self, relation_name=SPOE_AUTH_RELATION)
        self._oauth = OAuthRequirer(self, relation_name=OAUTH_RELATION)

        self.framework.observe(self.on.install, self._reconcile)
        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(self.on[OAUTH_RELATION].relation_created, self._reconcile)
        self.framework.observe(self.on[OAUTH_RELATION].relation_changed, self._reconcile)
        self.framework.observe(self._oauth.on.oauth_info_changed, self._reconcile)
        self.framework.observe(self._oauth.on.oauth_info_removed, self._reconcile)
        self.framework.observe(self.on[SPOE_AUTH_RELATION].relation_changed, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state and service configuration."""
        try:
            self.service.install()
            state = CharmState.from_charm(self)

            self._oauth.update_client_config(
                client_config=ClientConfig(
                    redirect_uri=f"https://{state.hostname}{OIDC_CALLBACK_PATH}",
                    scope=OIDC_SCOPE,
                    grant_types=["authorization_code"],
                )
            )
            oauth_information = OauthInformation.from_charm(self, self._oauth)
            if relation := self.model.get_relation(
                SPOE_AUTH_RELATION, oauth_information.spoe_auth_relation_id
            ):
                self._spoe_auth_provider.provide_spoe_auth_requirements(
                    relation=relation,
                    spop_port=SPOP_PORT,
                    event=HaproxyEvent.ON_FRONTEND_HTTP_REQUEST,
                    message_name=SPOE_AUTH_MESSAGE_NAME,
                    oidc_callback_port=OIDC_CALLBACK_PORT,
                    var_authenticated_scope=VAR_AUTHENTICATED_SCOPE,
                    var_authenticated=VAR_AUTHENTICATED,
                    var_redirect_url_scope=VAR_REDIRECT_URL_SCOPE,
                    var_redirect_url=VAR_REDIRECT_URL,
                    cookie_name=COOKIE_NAME,
                    hostname=state.hostname,
                    oidc_callback_path=OIDC_CALLBACK_PATH,
                )
            self.service.reconcile(charm_state=state, oauth_information=oauth_information)
            self.unit.status = ops.ActiveStatus()

        except InvalidCharmConfigError as exc:
            logger.exception("Charm state validation failed")
            self.unit.status = ops.BlockedStatus(f"Configuration error: {exc}")
        except SpoeAuthServiceConfigError as exc:
            logger.exception("Error configuring the haproxy-spoe-auth service.")
            self.unit.status = ops.BlockedStatus(f"Service configuration failed: {exc}")


if __name__ == "__main__":  # pragma: nocover
    ops.main(HaproxySpoeAuthCharm)
