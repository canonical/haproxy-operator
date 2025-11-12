# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The haproxy-spoe-auth service module."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from state.charm_state import CharmState
from state.oauth import OAuthInformation

SNAP_NAME = "haproxy-spoe-auth"
SERVICE_NAME = "haproxy-spoe-auth"
CONFIG_PATH = Path("/var/snap/haproxy-spoe-auth/current/config.yaml")
CONFIG_TEMPLATE = "config.yaml.j2"

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

    def install(self) -> None:
        """Install the haproxy-spoe-auth snap.

        Raises:
            SpoeAuthServiceInstallError: When snap installation fails.
        """
        try:
            # Import here to avoid issues when snap module is not available
            import subprocess  # nosec B404

            subprocess.run(  # nosec B603
                ["snap", "install", SNAP_NAME, "--edge"],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Successfully installed %s snap", SNAP_NAME)
        except Exception as exc:
            raise SpoeAuthServiceInstallError(
                f"Failed to install {SNAP_NAME} snap: {exc}"
            ) from exc

    def is_active(self) -> bool:
        """Check if the service is active.

        Returns:
            True if the service is running, False otherwise.
        """
        try:
            import subprocess  # nosec B404

            result = subprocess.run(  # nosec B603
                ["snap", "services", SNAP_NAME],
                check=True,
                capture_output=True,
                text=True,
            )
            return "active" in result.stdout
        except Exception:
            return False

    def reconcile(self, charm_state: CharmState, oauth_info: OAuthInformation) -> None:
        """Reconcile the service configuration.

        Args:
            charm_state: The current charm state.
            oauth_info: OAuth integration information.

        Raises:
            SpoeAuthServiceConfigError: When configuration fails.
        """
        try:
            self._render_config(charm_state, oauth_info)
            self._restart_service()
            logger.info("Successfully reconciled %s service", SERVICE_NAME)
        except Exception as exc:
            raise SpoeAuthServiceConfigError(f"Failed to reconcile service: {exc}") from exc

    def _render_config(self, charm_state: CharmState, oauth_info: OAuthInformation) -> None:
        """Render the configuration file.

        Args:
            charm_state: The current charm state.
            oauth_info: OAuth integration information.
        """
        env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(),
        )
        template = env.get_template(CONFIG_TEMPLATE)

        config_content = template.render(
            spoe_address=charm_state.spoe_address,
            oauth_enabled=oauth_info.oauth_data is not None,
            oauth_data=oauth_info.oauth_data if oauth_info.oauth_data else {},
        )

        # Ensure parent directory exists
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(config_content, encoding="utf-8")
        logger.info("Configuration written to %s", CONFIG_PATH)

    def _restart_service(self) -> None:
        """Restart the service."""
        import subprocess  # nosec B404

        subprocess.run(  # nosec B603
            ["snap", "restart", SNAP_NAME],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Service %s restarted", SERVICE_NAME)
