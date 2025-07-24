# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm state."""

import itertools
import logging
import typing
from enum import StrEnum

# bandit flags import subprocess as a low security issue
# We disable it here as it's simply a heads-up for potential issues
from subprocess import STDOUT, CalledProcessError, check_output  # nosec

import ops
from charms.haproxy.v1.haproxy_route import HaproxyRouteProvider
from charms.traefik_k8s.v1.ingress_per_unit import IngressPerUnitProvider
from charms.traefik_k8s.v2.ingress import IngressPerAppProvider
from pydantic import Field, ValidationError, field_validator
from pydantic.dataclasses import dataclass

from http_interface import HTTPRequirer

from .exception import CharmStateValidationBaseError

logger = logging.getLogger()


class HaproxyTooManyIntegrationsError(CharmStateValidationBaseError):
    """Exception raised when haproxy is in an invalid state with too many integrations."""


class ProxyMode(StrEnum):
    """StrEnum of possible http_route types.

    Attrs:
        HAPROXY_ROUTE: When haproxy-route is related.
        INGRESS: when ingress is related.
        INGRESS_PER_UNIT: when ingress-per-unit is related.
        LEGACY: when reverseproxy is related.
        NOPROXY: when haproxy should return a default page.
        INVALID: when the charm state is invalid.
    """

    HAPROXY_ROUTE = "haproxy-route"
    INGRESS = "ingress"
    INGRESS_PER_UNIT = "ingress-per-unit"
    LEGACY = "legacy"
    NOPROXY = "noproxy"
    INVALID = "invalid"


class InvalidCharmConfigError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


@dataclass(frozen=True)
class CharmState:
    """A component of charm state that contains the charm's configuration and mode.

    Attributes:
        mode: The current proxy mode of the charm.
        global_max_connection: The maximum per-process number of concurrent connections.
        Must be between 0 and "fs.nr_open" sysctl config.
    """

    mode: ProxyMode
    global_max_connection: int = Field(gt=0, alias="global_max_connection")

    @field_validator("global_max_connection")
    @classmethod
    def validate_global_max_conn(cls, global_max_connection: int) -> int:
        """Validate global_max_connection config.

        Args:
            global_max_connection: The config to validate.

        Raises:
            ValueError: When the configured value is not between 0 and "fs.file-max".

        Returns:
            int: The validated global_max_connection config.
        """
        try:
            # No user input so we're disabling bandit rule here as it's considered safe
            output = check_output(  # nosec: B603
                ["/usr/sbin/sysctl", "fs.file-max"], stderr=STDOUT, universal_newlines=True
            ).splitlines()
        except CalledProcessError:
            logger.exception("Cannot get system's max file descriptor value, skipping check.")
            return global_max_connection

        # Validate the configured max connection against the system's fd hard-limit
        _, _, fs_file_max = output[0].partition("=")
        if not fs_file_max:
            logger.warning("Error parsing sysctl output, skipping check.")
            return global_max_connection

        if fs_file_max and global_max_connection > int(fs_file_max.strip()):
            raise ValueError
        return global_max_connection

    @staticmethod
    def _validate_state(
        ingress_provider: IngressPerAppProvider,
        ingress_per_unit_provider: IngressPerUnitProvider,
        haproxy_route_provider: HaproxyRouteProvider,
        reverseproxy_requirer: HTTPRequirer,
    ) -> ProxyMode:
        """Validate if all the necessary preconditions are fulfilled.

        Args:
            ingress_provider: The ingress provider.
            ingress_per_unit_provider: The ingress per unit provider.
            haproxy_route_provider: The haproxy route provider.
            reverseproxy_requirer: The reverse proxy requirer.

        Raises:
            HaproxyTooManyIntegrationsError: when there are too many integrations and
            haproxy is in an invalid state.

        Returns:
            ProxyMode: The resulting proxy mode.
        """
        is_ingress_related = bool(ingress_provider.relations)
        is_ingress_per_unit_related = bool(ingress_per_unit_provider.relations)
        is_legacy_related = bool(reverseproxy_requirer.relations)
        is_haproxy_route_related = bool(haproxy_route_provider.relations)

        if (
            is_ingress_per_unit_related
            + is_ingress_related
            + is_legacy_related
            + is_haproxy_route_related
            > 1
        ):
            msg = (
                "Only one integration out of 'ingress', 'ingress-per-unit', "
                "'reverseproxy' or 'haproxy-route' can be active at a time."
            )
            logger.error(msg)
            raise HaproxyTooManyIntegrationsError(msg)

        if is_ingress_related:
            return ProxyMode.INGRESS

        if is_ingress_per_unit_related:
            return ProxyMode.INGRESS_PER_UNIT

        if is_legacy_related:
            return ProxyMode.LEGACY

        if is_haproxy_route_related:
            return ProxyMode.HAPROXY_ROUTE

        return ProxyMode.NOPROXY

    @classmethod
    def from_charm(  # pylint: disable=too-many-arguments, too-many-positional-arguments
        cls,
        charm: ops.CharmBase,
        ingress_provider: IngressPerAppProvider,
        ingress_per_unit_provider: IngressPerUnitProvider,
        haproxy_route_provider: HaproxyRouteProvider,
        reverseproxy_requirer: HTTPRequirer,
    ) -> "CharmState":
        """Create a CharmState class from a charm instance.

        Args:
            charm: The haproxy charm.
            ingress_provider: The ingress provider.
            ingress_per_unit_provider: The ingress per unit provider.
            haproxy_route_provider: The haproxy route provider.
            reverseproxy_requirer: The reverse proxy requirer.

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.

        Returns:
            CharmState: Instance of the charm state component.
        """
        global_max_connection = typing.cast(int, charm.config.get("global-maxconn"))
        try:
            return cls(
                mode=cls._validate_state(
                    ingress_provider,
                    ingress_per_unit_provider,
                    haproxy_route_provider,
                    reverseproxy_requirer,
                ),
                global_max_connection=global_max_connection,
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
