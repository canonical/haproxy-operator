# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

import typing
from unittest.mock import MagicMock

import pytest
from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    PrivateKey,
)
from ops.testing import Harness

from state.tls import TLSInformation, TLSNotReadyError
from tls_relation import TLSRelationService

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


def test_tls_information_integration_missing(harness: Harness):
    """arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSNotReadyError is raised.
    """
    harness.begin()
    with pytest.raises(TLSNotReadyError):
        TLSInformation.from_charm(harness.charm, harness.charm.certificates)


def test_get_provider_cert_with_hostname(
    harness: Harness, mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey]
):
    """arrange: Given a haproxy charm with mocked certificate.
    act: Run get_provider_cert_with_hostname with the correct hostname.
    assert: The correct provider certificate is returned.
    """
    mock_certificate, _ = mock_certificate_and_key
    harness.begin()
    harness.charm.certificates.certificate_requests = [
        CertificateRequestAttributes(
            common_name=TEST_EXTERNAL_HOSTNAME_CONFIG,
        )
    ]
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    assert str(
        tls_relation.get_provider_cert_with_hostname(TEST_EXTERNAL_HOSTNAME_CONFIG).certificate
    ) == str(mock_certificate)


@pytest.mark.usefixtures("mock_certificate_and_key")
def test_get_provider_cert_with_invalid_hostname(harness: Harness):
    """arrange: Given a haproxy charm with mocked certificate.
    act: Run get_provider_cert_with_hostname with an invalid hostname.
    assert: None is returned.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    assert tls_relation.get_provider_cert_with_hostname("") is None


def test_certificate_available(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
):
    """arrange: Given a haproxy charm.
    act: Run certificate_available.
    assert: write_certificate_to_unit method is called with correct parameter.
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    harness.begin()
    harness.charm.certificates.certificate_requests = [
        CertificateRequestAttributes(
            common_name=TEST_EXTERNAL_HOSTNAME_CONFIG,
            sans_dns=frozenset([TEST_EXTERNAL_HOSTNAME_CONFIG]),
        )
    ]

    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    write_cert_mock = MagicMock()
    monkeypatch.setattr(
        "tls_relation.TLSRelationService.write_certificate_to_unit", write_cert_mock
    )

    tls_information = TLSInformation(
        external_hostname=TEST_EXTERNAL_HOSTNAME_CONFIG,
        tls_cert_and_ca_chain={
            TEST_EXTERNAL_HOSTNAME_CONFIG: (mock_certificate, [mock_certificate])
        },
        private_key=mock_private_key,
    )
    tls_relation.certificate_available(tls_information)
    write_cert_mock.assert_called_once_with(
        certificate=mock_certificate, chain=[mock_certificate], private_key=mock_private_key
    )


def test_write_certificate_to_unit(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
):
    """arrange: Given a charm with mocked certificate and private_key + password.
    act: Run write_certificate_to_unit.
    assert: Path.write_text is called with the correct file content (cert + decrypted key).
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    path_mkdir_mock = MagicMock()
    write_text_mock = MagicMock()
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    monkeypatch.setattr("pathlib.Path.unlink", MagicMock(return_value=False))
    monkeypatch.setattr("pathlib.Path.mkdir", path_mkdir_mock)
    monkeypatch.setattr("pathlib.Path.write_text", write_text_mock)
    monkeypatch.setattr("os.chmod", MagicMock())
    monkeypatch.setattr("pwd.getpwnam", MagicMock())
    monkeypatch.setattr("os.chown", MagicMock())

    tls_relation.write_certificate_to_unit(mock_certificate, [mock_certificate], mock_private_key)
    pem_file_content = (
        f"{str(mock_certificate)}\n"
        f"{'\n'.join([str(cert) for cert in [mock_certificate]])}\n"
        f"{str(mock_private_key)}"
    )
    write_text_mock.assert_called_once_with(pem_file_content, encoding="utf-8")
