# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for functions containing charm utilities."""

import functools
import logging
import typing

import ops

from state.exception import CharmStateValidationBaseError
from state.tls import TLSNotReadyError

logger = logging.getLogger(__name__)

C = typing.TypeVar("C", bound=ops.CharmBase)


def validate_config_and_tls(
    defer: bool = False, block_on_tls_not_ready: bool = False
) -> typing.Callable[
    [typing.Callable[[C, typing.Any], None]], typing.Callable[[C, typing.Any], None]
]:
    """Create a decorator that puts the charm in blocked state if the config is wrong.

    Args:
        defer: whether to defer the event.
        block_on_tls_not_ready: Whether to block the charm if TLS is not ready.

    Returns:
        the function decorator.
    """

    def decorator(
        method: typing.Callable[[C, typing.Any], None]
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
            except CharmStateValidationBaseError as exc:
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
                if block_on_tls_not_ready:
                    instance.unit.status = ops.BlockedStatus(str(exc))
                logger.exception("Not ready to handle TLS.")
                return None

        return wrapper

    return decorator
