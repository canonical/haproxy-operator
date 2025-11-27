# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy-spoe-auth service module."""

import logging
from pathlib import Path

from charmlibs import snap
from jinja2 import Environment, FileSystemLoader, select_autoescape

from state import CharmState, OauthInformation

CONFIG_PATH = Path("/var/snap/haproxy-spoe-auth/current/config.yaml")
CONFIG_TEMPLATE = "config.yaml.j2"
COOKIE_NAME = "authsession"
OIDC_CALLBACK_PATH = "/oauth2/callback"
OIDC_CALLBACK_PORT = 5000
SNAP_CHANNEL = "latest/edge"
SNAP_NAME = "haproxy-spoe-auth"
SPOP_PORT = 8081

logger = logging.getLogger(__name__)


class SpoeAuthServiceInstallError(Exception):
    """Exception raised when snap installation fails."""


class SpoeAuthServiceConfigError(Exception):
    """Exception raised when service configuration fails."""


class SpoeAuthService:
    """HAProxy SPOE Auth service class."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._template_dir = Path(__file__).parent.parent / "templates"
        cache = snap.SnapCache()
        self.haproxy_spoe_auth_snap = cache[SNAP_NAME]

    def install(self) -> None:
        """Install the haproxy-spoe-auth snap.

        Raises:
            SpoeAuthServiceInstallError: When snap installation fails.
        """
        try:
            if not self.haproxy_spoe_auth_snap.present:
                self.haproxy_spoe_auth_snap.ensure(snap.SnapState.Latest, channel=SNAP_CHANNEL)
            self.haproxy_spoe_auth_snap.restart(reload=True)
        except snap.SnapError as exc:
            logger.error(
                "An exception occurred when installing the haproxy-spoe-auth snap: %s",
                str(exc),
            )
            raise SpoeAuthServiceInstallError("Failed to install haproxy-spoe-auth snap") from exc

    def reconcile(self, charm_state: CharmState, oauth_information: OauthInformation) -> None:
        """Reconcile the service configuration.

        Args:
            charm_state: The charm state.
            oauth_information: OAuth integration information.

        Raises:
            SpoeAuthServiceConfigError: When configuration fails.
        """
        try:
            self._render_config(charm_state, oauth_information)
            self.haproxy_spoe_auth_snap.restart(reload=True)
        except Exception as exc:
            raise SpoeAuthServiceConfigError(f"Failed to reconcile service: {exc}") from exc

    def _render_config(self, charm_state: CharmState, oauth_information: OauthInformation) -> None:
        """Render the configuration file.

        Args:
            charm_state: The charm state.
            oauth_information: OAuth integration information.
        """
        env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template(CONFIG_TEMPLATE)
        config_content = template.render(
            client_id=oauth_information.client_id,
            client_secret=oauth_information.client_secret,
            cookie_name=COOKIE_NAME,
            encryption_secret=charm_state.encryption_secret,
            hostname=charm_state.hostname,
            issuer_url=oauth_information.issuer_url,
            oidc_callback_path=OIDC_CALLBACK_PATH,
            oidc_callback_port=OIDC_CALLBACK_PORT,
            signature_secret=charm_state.signature_secret,
            spop_port=SPOP_PORT,
        )

        # Ensure parent directory exists
        CONFIG_PATH.write_text(config_content, encoding="utf-8")
