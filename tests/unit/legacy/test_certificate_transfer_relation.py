# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the certificate transfer relation in the charm."""

from unittest.mock import MagicMock

import pytest
from ops.testing import Harness

from tls_relation import TLSRelationService


def test_ca_certificates_available(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    """arrange: Given a haproxy integrated with a provider with CA certificates.
    act: Run _on_ca_certificates_available with the CA certificates.
    assert: The CA certificates are written to the unit.
    """
    harness.begin()
    tls_relation = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )
    write_cas_to_unit_mock = MagicMock()
    monkeypatch.setattr(
        "tls_relation.TLSRelationService.write_cas_to_unit", write_cas_to_unit_mock
    )

    mock_ca_certs_set = {
        "ca1",
        "ca2",
    }
    mock_get_all_certificates = MagicMock()
    mock_get_all_certificates.return_value = mock_ca_certs_set
    harness.add_relation("receive-ca-certs", "provider")
    harness.charm.recv_ca_certs.get_all_certificates = mock_get_all_certificates
    tls_relation.cas_to_trust_updated()

    write_cas_to_unit_mock.assert_called_once_with(mock_ca_certs_set)


def test_ca_certificates_removed(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
):
    """arrange: Given a haproxy integrated with a provider with CA certificates.
    act: Run remove_cas_from_unit.
    assert: The CA certificates are removed from the unit.
    """
    harness.begin()
    mock_cas_file = MagicMock()
    mock_cas_file.exists.return_value = True
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_FILE", mock_cas_file)

    tls_relation = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )
    tls_relation.remove_cas_from_unit()

    mock_cas_file.unlink.assert_called_once()
