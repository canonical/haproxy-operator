# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""SPOE authentication state management."""

import logging
import typing

import ops

logger = logging.getLogger(__name__)

SPOE_AUTH_RELATION = "spoe-auth"


class SpoeAuthAgent:
    """Information about a single SPOE auth agent."""

    def __init__(
        self,
        name: str,
        address: str,
        spop_port: int,
        oidc_callback_port: int,
    ):
        """Initialize SpoeAuthAgent.

        Args:
            name: Agent name/identifier.
            address: Agent address.
            spop_port: Port for SPOP protocol communication.
            oidc_callback_port: Port for OIDC callback handling.
        """
        self.name = name
        self.address = address
        self.spop_port = spop_port
        self.oidc_callback_port = oidc_callback_port


class SpoeAuthInformation:
    """SPOE authentication information."""

    def __init__(
        self,
        enabled: bool,
        agents: typing.Optional[typing.List[SpoeAuthAgent]] = None,
        oidc_callback_path: typing.Optional[str] = None,
        oidc_callback_hostname: typing.Optional[str] = None,
        var_authenticated: typing.Optional[str] = None,
        var_redirect_url: typing.Optional[str] = None,
        spoe_config_path: typing.Optional[str] = None,
    ):
        """Initialize SpoeAuthInformation.

        Args:
            enabled: Whether SPOE authentication is enabled.
            agents: List of SPOE auth agents.
            oidc_callback_path: OIDC callback path.
            oidc_callback_hostname: OIDC callback hostname.
            var_authenticated: HAProxy variable name for authenticated flag.
            var_redirect_url: HAProxy variable name for redirect URL.
            spoe_config_path: Path to SPOE configuration file.
        """
        self.enabled = enabled
        self.agents = agents or []
        self.oidc_callback_path = oidc_callback_path
        self.oidc_callback_hostname = oidc_callback_hostname
        self.var_authenticated = var_authenticated
        self.var_redirect_url = var_redirect_url
        self.spoe_config_path = spoe_config_path

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "SpoeAuthInformation":
        """Create SpoeAuthInformation from charm.

        Args:
            charm: The charm instance.

        Returns:
            SpoeAuthInformation instance.
        """
        relation = charm.model.get_relation(SPOE_AUTH_RELATION)
        if not relation:
            return cls(enabled=False)

        # Get data from the relation application data
        if not relation.app:
            logger.warning("SPOE auth relation has no application data")
            return cls(enabled=False)

        app_data = relation.data[relation.app]
        oidc_callback_path = app_data.get("oidc-callback-path")
        oidc_callback_hostname = app_data.get("oidc-callback-hostname")
        var_authenticated = app_data.get("var-authenticated")
        var_redirect_url = app_data.get("var-redirect-url")
        spoe_config_path = app_data.get("spoe-config-path")

        # Get agent information from units
        agents = []
        for unit in relation.units:
            unit_data = relation.data[unit]
            agent_address = unit_data.get("agent-address")
            spop_port_str = unit_data.get("spop-port")
            oidc_callback_port_str = unit_data.get("oidc-callback-port")

            if agent_address and spop_port_str and oidc_callback_port_str:
                try:
                    spop_port = int(spop_port_str)
                    oidc_callback_port = int(oidc_callback_port_str)
                    agent_name = unit.name.replace("/", "-")
                    agents.append(
                        SpoeAuthAgent(
                            name=agent_name,
                            address=agent_address,
                            spop_port=spop_port,
                            oidc_callback_port=oidc_callback_port,
                        )
                    )
                    logger.info(
                        "SPOE auth agent %s configured at %s (SPOP:%s, OIDC:%s)",
                        agent_name,
                        agent_address,
                        spop_port,
                        oidc_callback_port,
                    )
                except ValueError as e:
                    logger.error("Invalid port values for agent %s: %s", unit.name, e)

        if not agents:
            logger.warning("SPOE auth relation exists but no valid agent data found")
            return cls(enabled=False)

        # Check if all required fields are present
        if not all(
            [
                oidc_callback_path,
                oidc_callback_hostname,
                var_authenticated,
                var_redirect_url,
                spoe_config_path,
            ]
        ):
            logger.warning("SPOE auth relation missing required configuration fields")
            return cls(enabled=False)

        logger.info("SPOE auth enabled with %d agent(s)", len(agents))
        return cls(
            enabled=True,
            agents=agents,
            oidc_callback_path=oidc_callback_path,
            oidc_callback_hostname=oidc_callback_hostname,
            var_authenticated=var_authenticated,
            var_redirect_url=var_redirect_url,
            spoe_config_path=spoe_config_path,
        )
