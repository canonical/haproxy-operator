# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the haproxy charm."""

import logging
from unittest.mock import MagicMock

import ops
import pytest
import scenario

import tls_relation
from charm import HAProxyCharm

logger = logging.getLogger(__name__)


def test_install(context_with_install_mock, base_state):
    """
    arrange: prepare some state with peer relation
    act: run start
    assert: status is active
    """
    context, (install_mock, reconcile_default_mock, *_) = context_with_install_mock
    state = ops.testing.State(**base_state)
    context.run(context.on.install(), state)
    install_mock.assert_called_once()
    reconcile_default_mock.assert_called_once()


def test_ingress_per_unit_mode_success(
    context_with_install_mock, base_state_with_ingress_per_unit
):
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


def test_ingress_mode_success(context_with_install_mock, base_state_with_ingress):
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


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ca_certificates_available(
    monkeypatch: pytest.MonkeyPatch, receive_ca_certs_relation, ca_certificate_and_key
):
    """
    arrange: Prepare a state with the receive-ca-cert.
    act: Run relation_changed for the receive-ca-cert relation.
    assert: The unit is active and the certificate in the relation was written to the file.
    """
    ca_certificate, _ = ca_certificate_and_key
    render_file_mock = MagicMock()
    monkeypatch.setattr("tls_relation.render_file", render_file_mock)
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    mock_cas_dir = MagicMock()
    mock_cas_dir.exists.return_value = False
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_DIR", mock_cas_dir)

    state = ops.testing.State(
        relations=frozenset({receive_ca_certs_relation}),
        leader=True,
        model=ops.testing.Model(name="haproxy-tutorial"),
        app_status=ops.testing.ActiveStatus(""),
        unit_status=ops.testing.ActiveStatus(""),
    )

    ctx = ops.testing.Context(HAProxyCharm)
    out = ctx.run(
        ctx.on.relation_changed(receive_ca_certs_relation),
        state,
    )
    mock_cas_dir.mkdir.assert_called_once()
    render_file_mock.assert_any_call(
        tls_relation.HAPROXY_CAS_FILE, ca_certificate.raw + "\n", 0o644
    )
    assert out.app_status == ops.testing.ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ca_certificates_removed(monkeypatch: pytest.MonkeyPatch, receive_ca_certs_relation):
    """
    arrange: Prepare a state with the receive-ca-cert and the external accesses mocked.
    act: Run relation_broken for the receive-ca-cert relation.
    assert: The CA certificates file is removed from the unit.
    """
    monkeypatch.setattr("haproxy.render_file", MagicMock())

    mock_cas_file = MagicMock()
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_FILE", mock_cas_file)

    state = ops.testing.State(
        relations=frozenset({receive_ca_certs_relation}),
        model=ops.testing.Model(name="haproxy-tutorial"),
        app_status=ops.testing.ActiveStatus(""),
        unit_status=ops.testing.ActiveStatus(""),
    )

    ctx = ops.testing.Context(HAProxyCharm)
    out = ctx.run(
        ctx.on.relation_broken(receive_ca_certs_relation),
        state,
    )

    mock_cas_file.unlink.assert_called_once()
    assert out.app_status == ops.testing.ActiveStatus("")
