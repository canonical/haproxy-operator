# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm configuration."""

import itertools
import logging
import typing

import ops
from charms.operator_libs_linux.v0 import sysctl
from pydantic import Field, ValidationError, field_validator
from pydantic.dataclasses import dataclass

logger = logging.getLogger()


class InvalidCharmConfigError(Exception):
    """Exception raised when a charm configuration is found to be invalid."""


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attributes:
        global_max_connection: The maximum per-process number of concurrent connections.
        Must be between 0 and "fs.nr-open" sysctl config.
    """

    global_max_connection: int = Field(alias="global_max_connection")

    @field_validator("global_max_connection")
    @classmethod
    def validate_global_max_conn(cls, global_max_connection: int) -> int:
        """Validate global_max_connection config.

        Args:
            global_max_connection: The config to validate.

        Raises:
            ValueError: When the configured value is not between 0 and "fs.nr-open.

        Returns:
            int: The validated global_max_connection config.
        """
        config = sysctl.Config(cls.__name__)
        max_open_files = config.get("fs.nr-open")
        if global_max_connection > max_open_files or global_max_connection < 0:
            raise ValueError
        return global_max_connection

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm: The gateway-api-integrator charm.

        Raises:
            InvalidCharmConfigError: When the charm's config is invalid.

        Returns:
            CharmConfig: Instance of the charm config state component.
        """
        global_max_connection = typing.cast(int, charm.config.get("global-maxconn"))

        try:
            return cls(
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
