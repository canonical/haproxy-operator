# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-spoe-auth-operator charm state."""

import logging
from enum import StrEnum

from pydantic import Field
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class InvalidCharmConfigError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


class ProxyMode(StrEnum):
    """StrEnum of possible authentication modes.

    Attrs:
        OAUTH: When oauth relation is established.
        NOAUTH: When no authentication is configured.
    """

    OAUTH = "oauth"
    NOAUTH = "noauth"


@dataclass(frozen=True)
class CharmState:
    """A component of charm state that contains the charm's configuration and mode.

    Attributes:
        mode: The current authentication mode of the charm.
        spoe_address: The address for SPOE agent to listen on.
    """

    mode: ProxyMode
    spoe_address: str = Field(alias="spoe_address")
