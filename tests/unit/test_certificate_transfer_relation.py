# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the certificate transfer relation in the charm."""

import json
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from charms.tls_certificates_interface.v4 import tls_certificates
from ops.testing import ActiveStatus, Context, Model, Relation, State

import tls_relation
from charm import HAProxyCharm


@pytest.fixture
def mocks_external_calls(monkeypatch: pytest.MonkeyPatch):
    """Mock all external processes calls not relevant for the unit test."""
    monkeypatch.setattr("haproxy.HAProxyService._validate_haproxy_config", MagicMock())
    monkeypatch.setattr("haproxy.render_file", MagicMock())


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ca_certificates_available(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Prepare a state with the receive-ca-cert.
    act: Run relation_changed for the receive-ca-cert relation.
    assert: The unit is active and the certificate in the relation was written to the file.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("tls_relation.render_file", render_file_mock)

    mock_cas_dir = MagicMock()
    mock_cas_dir.exists.return_value = False
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_DIR", mock_cas_dir)

    ca = tls_certificates.generate_ca(
        tls_certificates.generate_private_key(), timedelta(days=10), "caname"
    )
    receive_ca_certs_relation = Relation(
        endpoint="receive-ca-certs",
        interface="certificate_transfer",
        remote_app_name="self-signed-certificates",
        remote_app_data={
            "certificates": json.dumps([ca.raw]),
            "version": "1",
        },
    )

    state = State(
        relations=frozenset({receive_ca_certs_relation}),
        leader=True,
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    ctx = Context(HAProxyCharm)
    out = ctx.run(
        ctx.on.relation_changed(receive_ca_certs_relation),
        state,
    )

    mock_cas_dir.exists.assert_called_once()
    mock_cas_dir.mkdir.assert_called_once()
    render_file_mock.assert_any_call(tls_relation.HAPROXY_CAS_FILE, ca.raw + "\n", 0o644)
    assert out.app_status == ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ca_certificates_removed(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Prepare a state with the receive-ca-cert and the external accesses mocked.
    act: Run relation_broken for the receive-ca-cert relation.
    assert: The CA certificates file is removed from the unit.
    """
    mock_cas_file = MagicMock()
    mock_cas_file.exists.return_value = True
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_FILE", mock_cas_file)

    ca = tls_certificates.generate_ca(
        tls_certificates.generate_private_key(), timedelta(days=10), "ca"
    )
    receive_ca_certs_relation = Relation(
        endpoint="receive-ca-certs",
        interface="certificate_transfer",
        remote_app_name="self-signed-certificates",
        remote_app_data={
            "certificates": json.dumps([ca.raw]),
            "version": "1",
        },
    )

    state = State(
        relations=frozenset({receive_ca_certs_relation}),
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    ctx = Context(HAProxyCharm)
    out = ctx.run(
        ctx.on.relation_broken(receive_ca_certs_relation),
        state,
    )

    mock_cas_file.unlink.assert_called_once()
    assert out.app_status == ActiveStatus("")
