# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for functions containing charm utilities."""

import functools
import logging
import typing

import ops
from charmlibs.snap import SnapError
from pydantic import ValidationError

from policy import HaproxyRoutePolicyAPIError, HaproxyRoutePolicyDatabaseMigrationError
from state.database import DatabaseRelationMissingError, DatabaseRelationNotReadyError
from state.policy import (
    DjangoAdminCredentialsInvalidError,
    DjangoAdminCredentialsMissingError,
    DjangoSecretKeyMissingError,
    PeerRelationMissingError,
)

logger = logging.getLogger(__name__)

C = typing.TypeVar("C", bound=ops.CharmBase)


def handle_charm_exceptions(
    method: typing.Callable[[C, typing.Any], None],
) -> typing.Callable[[C, typing.Any], None]:
    """Create a decorator that puts the charm in blocked state if the config is wrong.

    Args:
        method: observer method to wrap.

    Returns:
        the function wrapper.
    """

    @functools.wraps(method)
    def wrapper(instance: C, *args: typing.Any) -> None:
        """Block the charm if the config is wrong.

        Args:
            instance: the instance of the class with the hook method.
            args: Additional events

        Returns:
            The value returned from the original function. That is, None.
        """
        try:
            return method(instance, *args)
        except DatabaseRelationMissingError:
            instance.unit.status = ops.BlockedStatus("Missing database relation.")
            return
        except DatabaseRelationNotReadyError:
            logger.exception("Database relation not ready")
            instance.unit.status = ops.WaitingStatus("waiting for complete database relation.")
            return
        except PeerRelationMissingError:
            logger.exception("Peer relation missing")
            instance.unit.status = ops.WaitingStatus("Waiting for peer relation.")
            return
        except (
            DjangoSecretKeyMissingError,
            DjangoAdminCredentialsMissingError,
            DjangoAdminCredentialsInvalidError,
        ):
            logger.exception("Django shared configuration not ready")
            instance.unit.status = ops.WaitingStatus(
                "Waiting for complete shared configuration from leader."
            )
            return
        except (SnapError, HaproxyRoutePolicyDatabaseMigrationError) as exc:
            logger.exception("Failed to reconcile haproxy-route-policy service")
            instance.unit.status = ops.BlockedStatus(f"reconciliation failed: {exc}")
            return
        except HaproxyRoutePolicyAPIError as exc:
            logger.exception("Policy service API error")
            instance.unit.status = ops.BlockedStatus(f"policy service error: {exc.message}")
            return
        except ValidationError:
            logger.exception("Invalid haproxy-route-policy relation data")
            instance.unit.status = ops.WaitingStatus(
                "Waiting for valid haproxy-route-policy relation data"
            )
            return

    return wrapper
