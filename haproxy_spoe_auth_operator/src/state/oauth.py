# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""OAuth relation state management."""

import logging
from typing import Optional

from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class OAuthDataValidationError(CharmStateValidationBaseError):
    """Exception raised when OAuth relation data validation fails."""


@dataclass(frozen=True)
class OAuthData:
    """OAuth relation data.

    Attributes:
        client_id: The OAuth client ID.
        client_secret: The OAuth client secret.
        provider_url: The OAuth provider URL.
    """

    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    provider_url: str = Field(min_length=1)


@dataclass(frozen=True)
class OAuthInformation:
    """OAuth integration information.

    Attributes:
        oauth_data: OAuth configuration data.
    """

    oauth_data: Optional[OAuthData]

    @classmethod
    def from_charm(cls, charm: "ops.CharmBase") -> "OAuthInformation":  # type: ignore # noqa: F821
        """Initialize OAuthInformation from charm.

        Args:
            charm: The charm instance.

        Returns:
            OAuthInformation instance.

        Raises:
            OAuthDataValidationError: When OAuth data validation fails.
        """
        oauth_relation = charm.model.get_relation("oauth")
        if not oauth_relation:
            return cls(oauth_data=None)

        try:
            relation_data = oauth_relation.data[oauth_relation.app]
            oauth_data = OAuthData(
                client_id=relation_data.get("client_id", ""),
                client_secret=relation_data.get("client_secret", ""),
                provider_url=relation_data.get("provider_url", ""),
            )
            return cls(oauth_data=oauth_data)
        except (ValidationError, KeyError) as exc:
            raise OAuthDataValidationError(f"Invalid OAuth relation data: {exc}") from exc
