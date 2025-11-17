# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""SPOE authentication state management."""

import logging
import typing

import ops

logger = logging.getLogger(__name__)

SPOE_AUTH_RELATION = "spoe-auth"


class SpoeAuthInformation:
    """SPOE authentication information."""

    def __init__(
        self,
        enabled: bool,
        agent_address: typing.Optional[str] = None,
        agent_port: typing.Optional[int] = None,
    ):
        """Initialize SpoeAuthInformation.

        Args:
            enabled: Whether SPOE authentication is enabled.
            agent_address: Address of the SPOE authentication agent.
            agent_port: Port of the SPOE authentication agent.
        """
        self.enabled = enabled
        self.agent_address = agent_address
        self.agent_port = agent_port

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

        # Get data from the relation
        # The spoe-auth provider should provide the agent address and port
        for unit in relation.units:
            unit_data = relation.data[unit]
            agent_address = unit_data.get("agent-address")
            agent_port_str = unit_data.get("agent-port")

            if agent_address and agent_port_str:
                try:
                    agent_port = int(agent_port_str)
                    logger.info("SPOE auth agent configured at %s:%s", agent_address, agent_port)
                    return cls(
                        enabled=True,
                        agent_address=agent_address,
                        agent_port=agent_port,
                    )
                except ValueError:
                    logger.error("Invalid agent port: %s", agent_port_str)

        logger.warning("SPOE auth relation exists but no valid agent data found")
        return cls(enabled=False)
