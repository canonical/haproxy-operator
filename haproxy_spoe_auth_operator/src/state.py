# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-spoe-auth-operator charm state."""

import logging
import secrets
import typing

import ops
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass

from lib.charms.hydra.v0.oauth import OAuthRequirer

logger = logging.getLogger(__name__)

SPOE_AUTH_RELATION = "spoe-auth"
AGENT_SECRETS_LABEL = "agent-secrets"


class InvalidCharmConfigError(Exception):
    """Exception raised when a charm configuration is found to be invalid."""


@dataclass(frozen=True)
class CharmState:
    """A component of charm state that contains the charm's configuration and mode.

    Attributes:
        hostname: The hostname of the charm.
        client_id: The OAuth client ID.
        client_secret: The OAuth client secret.
        issuer_url: The OAuth issuer URL.
    """

    hostname: str = Field(description="The hostname part of the redirect URL.")
    signature_secret: str = Field(
        description="Secret used for signing by the SPOE agent.", min_length=1
    )
    encryption_secret: str = Field(
        description="Secret used for encrypting by the SPOE agent.", min_length=1
    )

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
    ) -> "CharmState":
        """Create a CharmState class from a charm instance.

        Args:
            charm: The spoe-auth agent charm.

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.

        Returns:
            CharmState: Instance of the charm state component.
        """
        hostname = typing.cast(str, charm.config.get("hostname"))
        signature_secret = None
        encryption_secret = None
        try:
            secret = charm.model.get_secret(label=AGENT_SECRETS_LABEL)
            signing_and_encryption_secrets = secret.get_content(refresh=True)
            signature_secret = signing_and_encryption_secrets.get("signature_secret")
            encryption_secret = signing_and_encryption_secrets.get("encryption_secret")
        except ops.SecretNotFoundError:
            signature_secret = secrets.token_urlsafe(32)
            encryption_secret = secrets.token_urlsafe(32)
            secret = charm.model.app.add_secret(
                content={
                    "signature_secret": signature_secret,
                    "encryption_secret": encryption_secret,
                },
                label=AGENT_SECRETS_LABEL,
            )

        if signature_secret is None or encryption_secret is None:
            raise InvalidCharmConfigError("Error fetching agent secrets.")

        try:
            return cls(
                hostname=hostname,
                signature_secret=signature_secret,
                encryption_secret=encryption_secret,
            )
        except ValidationError as exc:
            raise InvalidCharmConfigError("Invalid configuration") from exc


@dataclass(frozen=True)
class OauthInformation:
    """A component of charm state that contains the charm's configuration and mode.

    Attributes:
        client_id: The OAuth client ID.
        client_secret: The OAuth client secret.
        issuer_url: The OAuth issuer URL.
        spoe_auth_relation: The spoe-auth relation.
    """

    issuer_url: str = Field(description="The OAuth issuer URL.", min_length=1)
    client_id: str = Field(description="The OAuth client ID.", min_length=1)
    client_secret: str = Field(description="The OAuth client secret.", min_length=1)
    spoe_auth_relation: ops.Relation = Field(description="The spoe-auth relation.")

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        oauth: OAuthRequirer,
    ) -> "OauthInformation":
        """Create a CharmState class from a charm instance.

        Args:
            charm: The haproxy charm.
            oauth: The OAuthRequirer instance.

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.

        Returns:
            CharmState: Instance of the charm state component.
        """
        spoe_auth_relation = charm.model.get_relation(SPOE_AUTH_RELATION)
        if spoe_auth_relation is None:
            logger.error("spoe-auth relation missing.")
            raise InvalidCharmConfigError("spoe-auth relation missing.")

        oauth_provider_information = oauth.get_provider_info()
        if (
            oauth_provider_information is None
            or oauth_provider_information.client_id is None
            or oauth_provider_information.client_secret is None
        ):
            raise InvalidCharmConfigError("Waiting for complete oauth relation data.")

        try:
            return cls(
                issuer_url=oauth_provider_information.issuer_url,
                client_id=oauth_provider_information.client_id,
                client_secret=oauth_provider_information.client_secret,
                spoe_auth_relation=spoe_auth_relation,
            )
        except ValidationError as exc:
            raise InvalidCharmConfigError("Invalid configuration") from exc
