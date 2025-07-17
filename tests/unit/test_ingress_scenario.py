# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the ingress mode of haproxy charm."""

import logging

import ops
import scenario

logger = logging.getLogger(__name__)


def test_ingress(context_with_install_mock, base_state_with_ingress):
    """
    arrange: prepare some state with ingress relation
    act: trigger config changed hook
    assert: reconcile ingress is called once
    """
    context, (*_, reconcile_ingress_mock) = context_with_install_mock
    state = ops.testing.State(**base_state_with_ingress)
    context.run(context.on.config_changed(), state)
    reconcile_ingress_mock.assert_called_once()


def test_ingress_data_validation_error(context_with_install_mock, base_state_with_ingress):
    """
    arrange: prepare some state with ingress relation
    act: trigger config changed hook
    assert: haproxy is in a blocked state
    """
    context, _ = context_with_install_mock
    base_state_with_ingress["relations"][1] = scenario.Relation(
        endpoint="ingress", remote_app_name="requirer", remote_app_data={}
    )
    state = ops.testing.State(**base_state_with_ingress)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.testing.BlockedStatus(
        "Validation of ingress relation data failed."
    )
