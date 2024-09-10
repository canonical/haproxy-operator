# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm configuration."""

import itertools
import logging
import typing
from enum import StrEnum
import re
import ops
from pydantic import Field, ValidationError
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError
from tls import TLS_CERTIFICATES_INTEGRATION

logger = logging.getLogger()
INGRESS_RELATION = "ingress"
REVERSE_PROXY_RELATION = "reverseproxy"
EXTERNAL_HOSTNAME_MATCH = r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"


class ProxyMode(StrEnum):
    """StrEnum of haproxy charm proxy modes.

    Attrs:
        INGRESS: ingress.
        LEGACY: legacy.
        NOPROXY: noproxy.
    """

    INGRESS = "ingress"
    LEGACY = "legacy"
    NOPROXY = "noproxy"


class InvalidCharmConfigError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


class RelationConflictError(CharmStateValidationBaseError):
    """Exception raised when the charm established relations that can't work together."""


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attributes:
        global_max_connection: The configured gateway class.
        haproxy_frontend_prefix: The prefix for haproxy frontend stanzas.
        external_hostname: The configured hostname for haproxy (required under ingress mode).
        proxy_mode: The charm's proxy mode (ingress or legacy)
    """

    global_max_connection: int = Field(gt=0)
    haproxy_frontend_prefix: str
    external_hostname: str
    proxy_mode: str

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.
            RelationConflictError: When both ingress and reverseproxy relation is established.

        Returns:
            CharmConfig: Instance of the charm config state component.
        """
        global_max_connection = typing.cast(int, charm.config.get("global-maxconn"))
        external_hostname = typing.cast(str, charm.config.get("external-hostname"))

        reverseproxy_relations = charm.model.relations[REVERSE_PROXY_RELATION]
        ingress_relations = charm.model.relations[INGRESS_RELATION]
        if reverseproxy_relations and ingress_relations:
            raise RelationConflictError(
                "The ingress and reverseproxy relation are mutually exclusive."
            )

        proxy_mode = ProxyMode.NOPROXY
        if reverseproxy_relations:
            proxy_mode = ProxyMode.LEGACY
        if ingress_relations:
            proxy_mode = ProxyMode.INGRESS
            if not charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION) or not re.match(
                EXTERNAL_HOSTNAME_MATCH, external_hostname
            ):
                raise InvalidCharmConfigError(
                    "external-hostname and certificates relation must be set to use ingress."
                )

        try:
            return cls(
                global_max_connection=global_max_connection,
                haproxy_frontend_prefix=charm.unit.name.replace("/", "-"),
                external_hostname=external_hostname,
                proxy_mode=proxy_mode,
            )
        except ValidationError as exc:
            error_field_str = ",".join(f"{field}" for field in get_invalid_config_fields(exc))
            raise InvalidCharmConfigError(f"invalid configuration: {error_field_str}") from exc


def get_invalid_config_fields(exc: ValidationError) -> typing.Set[int | str]:
    """Return a list on invalid config from pydantic validation error.

    Args:
        exc: The validation error exception.

    Returns:
        str: list of fields that failed validation.
    """
    error_fields = set(itertools.chain.from_iterable(error["loc"] for error in exc.errors()))
    return error_fields
