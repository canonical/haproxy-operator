# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit test fixtures for haproxy-spoe-auth-operator."""

from unittest.mock import MagicMock, patch

import ops.testing
import pytest


@pytest.fixture(name="context")
def fixture_context() -> ops.testing.Context:
    """Create a testing context for the charm.

    Returns:
        A Context object for testing.
    """
    from charm import HaproxySpoeAuthCharm

    return ops.testing.Context(
        HaproxySpoeAuthCharm,
        meta={
            "name": "haproxy-spoe-auth",
            "requires": {
                "oauth": {"interface": "oauth"},
            },
        },
        config={
            "options": {
                "spoe-address": {
                    "default": "127.0.0.1:3000",
                    "type": "string",
                }
            }
        },
    )


@pytest.fixture(name="base_state")
def fixture_base_state() -> dict:
    """Create a base state for testing.

    Returns:
        A dictionary representing the base state.
    """
    return {
        "config": {"spoe-address": "127.0.0.1:3000"},
    }


@pytest.fixture(name="context_with_mocks")
def fixture_context_with_mocks(
    context: ops.testing.Context,
) -> tuple[ops.testing.Context, tuple[MagicMock, MagicMock]]:
    """Create a context with mocked service methods.

    Args:
        context: The testing context.

    Returns:
        A tuple of the context and mocked methods.
    """
    with (
        patch("charm.SpoeAuthService.install") as install_mock,
        patch("charm.SpoeAuthService.reconcile") as reconcile_mock,
    ):
        yield context, (install_mock, reconcile_mock)
