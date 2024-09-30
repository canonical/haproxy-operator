# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import pytest
from ops.model import Secret, SecretNotFoundError
from ops.testing import Harness

from state.tls import TLSInformation, TLSNotReadyError
from tls_relation import (
    GetPrivateKeyError,
    InvalidCertificateError,
    TLSRelationService,
    _get_decrypted_key,
    get_hostname_from_cert,
)

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


def test_tls_information_integration_missing(harness: Harness):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSNotReadyError is raised.
    """
    harness.begin()
    with pytest.raises(TLSNotReadyError):
        TLSInformation.from_charm(harness.charm, harness.charm.certificates)


def test_generate_private_key(
    harness_with_mock_certificates_integration: Harness, juju_secret_mock: MagicMock
):
    """
    arrange: Given a haproxy charm with mock juju secret and certificates integration.
    act: Run generate private_key method.
    assert: set_content is called.
    """
    harness = harness_with_mock_certificates_integration
    harness.begin()

    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    tls_relation.generate_private_key(TEST_EXTERNAL_HOSTNAME_CONFIG)

    juju_secret_mock.set_content.assert_called_once()


def test_generate_private_key_assertion_error(harness: Harness):
    """
    arrange: Given a haproxy charm with missing certificates integration.
    act: Run generate private_key method.
    assert: AssertionError is raised.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    with pytest.raises(AssertionError):
        tls_relation.generate_private_key(TEST_EXTERNAL_HOSTNAME_CONFIG)


def test_generate_private_key_secret_not_found(
    harness_with_mock_certificates_integration: Harness, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a haproxy charm with missing certificates integration.
    act: Run generate private_key method.
    assert: The mocked create_secret method is called once.
    """
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(side_effect=SecretNotFoundError))
    created_secret_mock = MagicMock(spec=Secret)
    harness = harness_with_mock_certificates_integration

    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    tls_relation.application.add_secret = MagicMock(return_value=created_secret_mock)
    tls_relation.generate_private_key(TEST_EXTERNAL_HOSTNAME_CONFIG)
    created_secret_mock.grant.assert_called_once()


@pytest.mark.usefixtures("juju_secret_mock")
def test_request_certificate(
    harness_with_mock_certificates_integration: Harness, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a haproxy charm with mocked certificates integration and juju secret.
    act: Run request_certificate method.
    assert: request_certificate_creation mocked lib method is called once.
    """
    request_certificate_creation_mock = MagicMock()
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.request_certificate_creation"
        ),
        request_certificate_creation_mock,
    )
    harness = harness_with_mock_certificates_integration
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    tls_relation.request_certificate(TEST_EXTERNAL_HOSTNAME_CONFIG)

    request_certificate_creation_mock.assert_called_once()


def test_get_provider_cert_with_hostname(harness: Harness, mock_certificate: str):
    """
    arrange: Given a haproxy charm with mocked certificate.
    act: Run get_provider_cert_with_hostname with the correct hostname.
    assert: The correct provider certificate is returned.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    assert (
        tls_relation.get_provider_cert_with_hostname(TEST_EXTERNAL_HOSTNAME_CONFIG).certificate
        == mock_certificate
    )


@pytest.mark.usefixtures("mock_certificate")
def test_get_provider_cert_with_invalid_hostname(harness: Harness):
    """
    arrange: Given a haproxy charm with mocked certificate.
    act: Run get_provider_cert_with_hostname with an invalid hostname.
    assert: None is returned.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    assert tls_relation.get_provider_cert_with_hostname("") is None


def test_certificate_available(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a haproxy charm.
    act: Run certificate_available.
    assert: write_certificate_to_unit method is called with correct parameter.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    write_cert_mock = MagicMock()
    monkeypatch.setattr(
        "tls_relation.TLSRelationService.write_certificate_to_unit", write_cert_mock
    )
    tls_relation.certificate_available("cert")
    write_cert_mock.assert_called_once_with("cert")


@pytest.mark.usefixtures("juju_secret_mock")
def test_certificate_invalidated(
    harness: Harness, mock_certificate: str, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a charm with mocked certificate.
    act: Run certificate_invalidated.
    assert: Path.unlink is called once.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    path_unlink_mock = MagicMock()
    monkeypatch.setattr("pathlib.Path.unlink", path_unlink_mock)
    tls_relation.certificate_invalidated(mock_certificate)
    path_unlink_mock.assert_called_once()


@pytest.mark.usefixtures("juju_secret_mock")
def test_certificate_invalidated_provider_cert_param(
    harness: Harness, mock_certificate: str, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a charm with mocked certificate.
    act: Run certificate_invalidated with a provider cert as param.
    assert: Path.unlink is called once.
    """
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(side_effect=SecretNotFoundError))
    provider_cert_mock = MagicMock()
    provider_cert_mock.certificate = mock_certificate
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    path_unlink_mock = MagicMock()
    monkeypatch.setattr("pathlib.Path.unlink", path_unlink_mock)
    tls_relation.certificate_invalidated(provider_certificate=provider_cert_mock)
    path_unlink_mock.assert_called_once()


@pytest.mark.usefixtures("juju_secret_mock")
def test_certificate_invalidated_no_param(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a charm with mocked certificate.
    act: Run certificate_invalidated with an invalid hostname.
    assert: Path.unlink is not called.
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    path_unlink_mock = MagicMock()
    monkeypatch.setattr("pathlib.Path.unlink", path_unlink_mock)
    tls_relation.certificate_invalidated()
    path_unlink_mock.assert_not_called()


@pytest.mark.usefixtures("juju_secret_mock")
def test_certificate_invalidated_invalid_cert(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a charm with mocked certificate.
    act: Run certificate_invalidated with an invalid certificate.
    assert: Path.unlink is not called.
    """
    invalid_cert = "INVALID"
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    path_unlink_mock = MagicMock()
    monkeypatch.setattr("pathlib.Path.unlink", path_unlink_mock)
    tls_relation.certificate_invalidated(certificate=invalid_cert)
    path_unlink_mock.assert_not_called()


@pytest.mark.usefixtures("juju_secret_mock")
def test_write_certificate_to_unit(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    mock_certificate: str,
    private_key_and_password: tuple[str, str],
):
    """
    arrange: Given a charm with mocked certificate and private_key + password.
    act: Run write_certificate_to_unit.
    assert: Path.write_text is called with the correct file content (cert + decrypted key).
    """
    password, private_key = private_key_and_password
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

    tls_relation.write_certificate_to_unit(mock_certificate)
    decrypted_private_key = _get_decrypted_key(private_key, password)
    pem_file_content = f"{mock_certificate}\n{decrypted_private_key}"
    write_text_mock.assert_called_once_with(pem_file_content, encoding="utf-8")


@pytest.mark.usefixtures("juju_secret_mock")
def test_get_hostname_from_cert_invalid_cert(monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a charm with mocked certificate.
    act: Run certificate_invalidated with an invalid certificate.
    assert: InvalidCertificateError is correctly raised.
    """
    decoded_cert_mock = MagicMock()
    decoded_cert_mock.subject.get_attributes_for_oid = MagicMock(return_value=[])
    monkeypatch.setattr(
        "cryptography.x509.load_pem_x509_certificate", MagicMock(return_value=decoded_cert_mock)
    )
    with pytest.raises(InvalidCertificateError):
        get_hostname_from_cert("certificate")


@pytest.mark.usefixtures("juju_secret_mock")
def test_get_private_key_secret_not_found(harness: Harness, monkeypatch: pytest.MonkeyPatch):
    """
    arrange: Given a charm.
    act: Run _get_private_key which raises a SecretNotFoundError.
    assert: The charm correctly wraps the error and raise a GetPrivateKeyError.
    """
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(side_effect=SecretNotFoundError))
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    with pytest.raises(GetPrivateKeyError):
        # We disable the pylint warning here because we're testing that method
        tls_relation._get_private_key("hostname")  # pylint: disable=protected-access


@pytest.mark.parametrize(
    "use_valid_certificate",
    [
        pytest.param(True, id="Use valid certificate"),
        pytest.param(False, id="Use invalid certificate"),
    ],
)
@pytest.mark.usefixtures("juju_secret_mock")
def test_certificate_expiring(
    harness: Harness,
    mock_certificate: str,
    monkeypatch: pytest.MonkeyPatch,
    use_valid_certificate: bool,
):
    """
    arrange: Given a charm with mocked certificate and juju secret.
    act: Run certificate_expiring with a valid cert and a non valid one.
    assert: request_cert_renewal_mock is called if called with valid cert.
    """
    request_cert_renewal_mock = MagicMock()
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.request_certificate_renewal"
        ),
        request_cert_renewal_mock,
    )
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)

    cert = mock_certificate if use_valid_certificate else "INVALID"
    tls_relation.certificate_expiring(cert)

    if use_valid_certificate:
        request_cert_renewal_mock.assert_called_once()
