# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the haproxy-spoe-auth charm."""

import logging

import ops.testing

logger = logging.getLogger(__name__)


def test_install(context_with_install_mock):
    """Test charm install event.

    arrange: prepare base state
    act: run install hook
    assert: service install is called
    """
    context, install_mock = context_with_install_mock
    state = ops.testing.State(relations=[])
    context.run(context.on.install(), state)
    install_mock.assert_called_once()
