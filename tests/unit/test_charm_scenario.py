# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import logging

import ops

logger = logging.getLogger(__name__)


def test_install(context_with_install_mock, base_state):
    """
    arrange: prepare some state with peer relation
    act: run start
    assert: status is active
    """
    context, install_mock = context_with_install_mock
    state = ops.testing.State(**base_state)
    context.run(context.on.install(), state)
    install_mock.assert_called_once()
