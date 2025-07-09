# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the haproxy charm."""

import logging
from unittest.mock import patch

import ops
import pytest
from ops.testing import Context

from charm import HAProxyCharm

logger = logging.getLogger(__name__)


@pytest.fixture(name="context_with_reconcile_mock")
def context_with_install_mock_fixture():
    """Context relation fixture.

    Yield: The modeled haproxy-peers relation.
    """
    with (
        patch("haproxy.HAProxyService.reconcile_haproxy_route") as reconcile_mock,
        patch("tls_relation.TLSRelationService.write_certificate_to_unit"),
        patch("haproxy.HAProxyService.install"),
    ):
        yield (
            Context(
                charm_type=HAProxyCharm,
            ),
            reconcile_mock,
        )


def test_haproxy_route(context_with_reconcile_mock, base_state_haproxy_route):
    """
    arrange: prepare some state with peer relation
    act: run start
    assert: status is active
    """
    context, reconcile_mock = context_with_reconcile_mock
    state = ops.testing.State(**base_state_haproxy_route)
    context.run(context.on.config_changed(), state)
    reconcile_mock.assert_called_once()
