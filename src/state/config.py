# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm configuration."""

import itertools
import logging
import typing

# bandit flags import subprocess as a low security issue
# We disable it here as it's simply a heads-up for potential issues
from subprocess import STDOUT, CalledProcessError, check_output  # nosec

import ops
from pydantic import Field, ValidationError, field_validator
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError

logger = logging.getLogger()


class InvalidCharmConfigError(CharmStateValidationBaseError):
    """Exception raised when a charm configuration is found to be invalid."""


@dataclass(frozen=True)
class CharmConfig:
    """A component of charm state that contains the charm's configuration.

    Attributes:
        global_max_connection: The maximum per-process number of concurrent connections.
        Must be between 0 and "fs.nr_open" sysctl config.
    """

    global_max_connection: int = Field(alias="global_max_connection")

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
        if global_max_connection < 0:
            raise ValueError

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

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmConfig":
        """Create a CharmConfig class from a charm instance.

        Args:
            charm: The haproxy charm.

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
