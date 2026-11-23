# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for TLS relation and state handling."""

import typing
from unittest.mock import MagicMock

import pytest
from charmlibs.interfaces.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    PrivateKey,
)

from state.tls import HaproxyPeerRelationAppData, TLSInformation, TLSNotReadyError
from tls_relation import TLSRelationService

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"


def _build_certificates(
    requests: list[CertificateRequestAttributes],
    provider_certificates: list[MagicMock],
    private_key: PrivateKey,
) -> MagicMock:
    """Build a mock TLS certificates requirer."""
    certificates = MagicMock()
    certificates.relationship_name = "certificates"
    certificates.certificate_requests = requests
    certificates.get_assigned_certificates.return_value = (provider_certificates, private_key)
    return certificates


def test_tls_information_integration_missing():
    """arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSNotReadyError is raised.
    """
    charm = MagicMock()
    charm.model.get_relation.return_value = None
    certificates = _build_certificates([], [], MagicMock())

    with pytest.raises(TLSNotReadyError):
        TLSInformation.from_charm(charm, certificates)


def test_get_provider_cert_with_hostname(mock_certificate_and_key):
    """arrange: Given a haproxy charm with mocked certificate.
    act: Run get_provider_cert_with_hostname with the correct hostname.
    assert: The correct provider certificate is returned.
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    provider_certificate = MagicMock()
    provider_certificate.certificate = mock_certificate
    certificates = _build_certificates(
        [CertificateRequestAttributes(common_name=TEST_EXTERNAL_HOSTNAME_CONFIG)],
        [provider_certificate],
        mock_private_key,
    )
    tls_relation = TLSRelationService(MagicMock(), certificates, MagicMock())

    result = tls_relation.get_provider_cert_with_hostname(TEST_EXTERNAL_HOSTNAME_CONFIG)

    assert str(result.certificate) == str(mock_certificate)


def test_get_provider_cert_with_invalid_hostname(mock_certificate_and_key):
    """arrange: Given a haproxy charm with mocked certificate.
    act: Run get_provider_cert_with_hostname with an invalid hostname.
    assert: None is returned.
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    provider_certificate = MagicMock()
    provider_certificate.certificate = mock_certificate
    certificates = _build_certificates(
        [CertificateRequestAttributes(common_name=TEST_EXTERNAL_HOSTNAME_CONFIG)],
        [provider_certificate],
        mock_private_key,
    )
    tls_relation = TLSRelationService(MagicMock(), certificates, MagicMock())

    assert tls_relation.get_provider_cert_with_hostname("") is None


def test_certificate_available(
    monkeypatch: pytest.MonkeyPatch,
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
):
    """arrange: Given a haproxy charm.
    act: Run certificate_available.
    assert: write_certificate_to_unit method is called with correct parameter.
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    certificates = _build_certificates(
        [
            CertificateRequestAttributes(
                common_name=TEST_EXTERNAL_HOSTNAME_CONFIG,
                sans_dns=frozenset([TEST_EXTERNAL_HOSTNAME_CONFIG]),
            )
        ],
        [],
        mock_private_key,
    )
    tls_relation = TLSRelationService(MagicMock(), certificates, MagicMock())

    write_cert_mock = MagicMock()
    monkeypatch.setattr(
        "tls_relation.TLSRelationService.write_certificate_to_unit", write_cert_mock
    )
    monkeypatch.setattr("tls_relation.file_exists", MagicMock(return_value=False))

    tls_information = TLSInformation(
        hostnames=[TEST_EXTERNAL_HOSTNAME_CONFIG],
        tls_cert_and_ca_chain=HaproxyPeerRelationAppData(
            shared_certificates=[(mock_certificate, [mock_certificate])]
        ),
        private_key=str(mock_private_key),
    )
    tls_relation.certificate_available(tls_information)
    write_cert_mock.assert_called_once_with(
        certificate=mock_certificate, chain=[mock_certificate], private_key=str(mock_private_key)
    )


def test_write_certificate_to_unit(
    monkeypatch: pytest.MonkeyPatch,
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
):
    """arrange: Given a charm with mocked certificate and private_key + password.
    act: Run write_certificate_to_unit.
    assert: Path.write_text is called with the correct file content (cert + decrypted key).
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    write_text_mock = MagicMock()
    tls_relation = TLSRelationService(MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setattr("pathlib.Path.mkdir", MagicMock())
    monkeypatch.setattr("pathlib.Path.write_text", write_text_mock)
    monkeypatch.setattr("os.chmod", MagicMock())
    monkeypatch.setattr("pwd.getpwnam", MagicMock())
    monkeypatch.setattr("os.chown", MagicMock())
    chain_string = "\n".join([str(cert) for cert in [mock_certificate]])

    tls_relation.write_certificate_to_unit(
        mock_certificate, [mock_certificate], str(mock_private_key)
    )
    pem_file_content = f"{mock_certificate!s}\n{chain_string}\n{mock_private_key!s}"

    write_text_mock.assert_called_once_with(pem_file_content, encoding="utf-8")
