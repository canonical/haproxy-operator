# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm tls information."""

import typing

import ops
from pydantic import IPvAnyAddress, ValidationError, model_validator
from pydantic.dataclasses import dataclass
from typing_extensions import Self

from .exception import CharmStateValidationBaseError

HACLUSTER_INTEGRATION = "ha"
HAPROXY_PEER_INTEGRATION = "haproxy-peers"


class HAInformationValidationError(CharmStateValidationBaseError):
    """Exception raised when validation of the ha_information state component failed."""


@dataclass(frozen=True)
class HAInformation:
    """A component of charm state containing information about TLS.

    Attributes:ready
        ha_integration_ready: Whether the ha relation is ready.
        vip: The configured virtual IP address.
        haproxy_peer_integration_ready: Whether the haproxy peer integration is ready.
        configured_vip: Previously configured Virtual IP address. None if no vip was configured.
    """

    ha_integration_ready: bool
    vip: typing.Optional[IPvAnyAddress]
    haproxy_peer_integration_ready: bool
    configured_vip: typing.Optional[IPvAnyAddress]

    @model_validator(mode="after")
    def validate_vip_not_none_when_ha_integration_active(self) -> Self:
        """Validate that vip is configured when ha integration is active.

        Raises:
            ValueError: When ha integration is active but vip is not configured.

        Returns:
            Self: Validated model.
        """
        if self.ha_integration_ready and not self.vip:
            raise ValueError("vip needs to be configured in ha mode.")
        return self

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "HAInformation":
        """Get ha information from a charm instance.

        Args:
            charm: The haproxy charm.

        Raises:
            HAInformationValidationError: When validation of the state component failed.

        Returns:
            HAInformation: Information needed to configure ha.
        """
        ha_integration = charm.model.get_relation(HACLUSTER_INTEGRATION)
        vip = charm.config.get("vip")

        haproxy_peer_integration = charm.model.get_relation(HAPROXY_PEER_INTEGRATION)
        configured_vip = (
            haproxy_peer_integration.data[charm.unit].get("vip")
            if haproxy_peer_integration
            else None
        )

        try:
            # Ignore arg-type here because we want to pass a str and let pydantic do the validation
            return cls(
                ha_integration_ready=bool(ha_integration and ha_integration.units),
                vip=vip if vip else None,  # type: ignore
                haproxy_peer_integration_ready=bool(haproxy_peer_integration),
                configured_vip=configured_vip,  # type: ignore
            )
        except ValidationError as exc:
            raise HAInformationValidationError(str(exc)) from exc
