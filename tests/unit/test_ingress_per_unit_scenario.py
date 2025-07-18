# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the ingress-per-unit mode of haproxy charm."""

import logging

import ops
import scenario

logger = logging.getLogger(__name__)


def test_ingress_per_unit_success(context_with_install_mock, base_state_with_ingress_per_unit):
    """
    arrange: prepare some state with ingress per unit relation
    act: trigger config changed hook
    assert: reconcile_ingress is called once
    """
    context, (*_, reconcile_ingress_mock) = context_with_install_mock
    state = ops.testing.State(**base_state_with_ingress_per_unit)
    context.run(context.on.config_changed(), state)
    reconcile_ingress_mock.assert_called_once()


def test_ingress_per_unit_data_validation_error(
    context_with_install_mock, base_state_with_ingress_per_unit
):
    """
    arrange: prepare some state with ingress per unit relation
    act: trigger config changed hook
    assert: haproxy is in a blocked state
    """
    context, _ = context_with_install_mock
    base_state_with_ingress_per_unit["relations"][1] = scenario.Relation(
        endpoint="ingress-per-unit", remote_app_name="requirer", remote_units_data={0: {}}
    )
    state = ops.testing.State(**base_state_with_ingress_per_unit)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.testing.BlockedStatus(
        "Validation of ingress per unit relation data failed."
    )
