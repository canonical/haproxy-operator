# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for functions containing charm utilities."""

import functools
import logging
import typing

import ops
from charms.haproxy.v1.haproxy_route import HaproxyRouteInvalidRelationDataError

from haproxy import HaproxyValidateConfigError
from state.exception import CharmStateValidationBaseError
from state.tls import PrivateKeyNotGeneratedError, TLSNotReadyError

logger = logging.getLogger(__name__)

C = typing.TypeVar("C", bound=ops.CharmBase)


# We ignore flake8 complexity warning here because
# the decorator is complex by design as it needs to catch all exceptions
def validate_config_and_tls(  # noqa: C901
    defer: bool = False,
) -> typing.Callable[
    [typing.Callable[[C, typing.Any], None]], typing.Callable[[C, typing.Any], None]
]:
    """Create a decorator that puts the charm in blocked state if the config is wrong.

    Args:
        defer: whether to defer the event.

    Returns:
        the function decorator.
    """

    def decorator(
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
            event: ops.EventBase
            try:
                return method(instance, *args)
            except (CharmStateValidationBaseError, HaproxyRouteInvalidRelationDataError) as exc:
                if defer:
                    event, *_ = args
                    event.defer()
                logger.exception("Error setting up charm state.")
                instance.unit.status = ops.BlockedStatus(str(exc))
                return None
            except TLSNotReadyError as exc:
                if defer:
                    event, *_ = args
                    event.defer()
                instance.unit.status = ops.BlockedStatus(str(exc))
                logger.exception("Not ready to handle TLS.")
                return None
            except PrivateKeyNotGeneratedError as exc:
                if defer:
                    event, *_ = args
                    event.defer()
                instance.unit.status = ops.WaitingStatus(str(exc))
                logger.exception("Waiting for private key to be generated")
                return None
            except HaproxyValidateConfigError as exc:
                if defer:
                    event, *_ = args
                    event.defer()
                instance.unit.status = ops.WaitingStatus(str(exc))
                logger.exception(
                    (
                        "Validation of the HAproxy config failed."
                        "It is likely that some information are missing"
                        "waiting to reconcile: %s."
                    ),
                    str(exc),
                )
                return None

        return wrapper

    return decorator
