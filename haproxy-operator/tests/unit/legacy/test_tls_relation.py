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

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"


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
    tls_relation = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )
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
    tls_relation = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )
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

    tls_relation = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )

    write_cert_mock = MagicMock()
    monkeypatch.setattr(
        "tls_relation.TLSRelationService.write_certificate_to_unit", write_cert_mock
    )

    tls_information = TLSInformation(
        hostnames=[TEST_EXTERNAL_HOSTNAME_CONFIG],
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
    tls_relation = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )
    monkeypatch.setattr("pathlib.Path.unlink", MagicMock(return_value=False))
    monkeypatch.setattr("pathlib.Path.mkdir", path_mkdir_mock)
    monkeypatch.setattr("pathlib.Path.write_text", write_text_mock)
    monkeypatch.setattr("os.chmod", MagicMock())
    monkeypatch.setattr("pwd.getpwnam", MagicMock())
    monkeypatch.setattr("os.chown", MagicMock())
    chain_string = "\n".join([str(cert) for cert in [mock_certificate]])

    tls_relation.write_certificate_to_unit(mock_certificate, [mock_certificate], mock_private_key)
    pem_file_content = f"{mock_certificate!s}\n{chain_string}\n{mock_private_key!s}"

    write_text_mock.assert_called_once_with(pem_file_content, encoding="utf-8")


def test_share_certificates_via_peer_relation(
    harness: Harness,
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
):
    """arrange: Given a TLSRelationService and TLS information.
    act: Run share_certificates_via_peer_relation.
    assert: Peer relation app databag contains serialized certificate data.
    """
    mock_certificate, mock_private_key = mock_certificate_and_key
    harness.begin()
    harness.set_leader(True)
    tls_relation_service = TLSRelationService(
        harness.model, harness.charm.certificates, harness.charm.recv_ca_certs
    )
    hostname = "haproxy.internal"
    tls_information = TLSInformation(
        hostnames=[hostname],
        tls_cert_and_ca_chain={hostname: (mock_certificate, [mock_certificate])},
        private_key=str(mock_private_key),
    )

    peer_relation_id = harness.add_relation("haproxy-peers", "haproxy")
    peer_relation = harness.model.get_relation("haproxy-peers", peer_relation_id)
    assert peer_relation is not None

    tls_relation_service.share_certificates_via_peer_relation(peer_relation, tls_information)

    import json

    from tls_relation import PEER_TLS_KEY

    raw_data = peer_relation.data[harness.model.app].get(PEER_TLS_KEY)
    assert raw_data is not None
    data = json.loads(raw_data)
    assert data["hostnames"] == [hostname]
    assert hostname in data["certificates"]
    assert data["certificates"][hostname]["certificate"] == str(mock_certificate)
    assert data["private_key"] == str(mock_private_key)


def test_get_tls_information_from_peer_relation(
    harness: Harness,
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
):
    """arrange: Given a peer relation with certificate data in app databag.
    act: Run get_tls_information_from_peer_relation.
    assert: TLSInformation is correctly deserialized.
    """
    import json

    from tls_relation import PEER_TLS_KEY

    mock_certificate, mock_private_key = mock_certificate_and_key
    harness.begin()
    harness.set_leader(True)
    hostname = "haproxy.internal"
    peer_data = json.dumps(
        {
            "hostnames": [hostname],
            "certificates": {
                hostname: {
                    "certificate": str(mock_certificate),
                    "chain": [str(mock_certificate)],
                }
            },
            "private_key": str(mock_private_key),
        }
    )

    peer_relation_id = harness.add_relation("haproxy-peers", "haproxy")
    harness.update_relation_data(
        peer_relation_id, harness.model.app.name, {PEER_TLS_KEY: peer_data}
    )
    peer_relation = harness.model.get_relation("haproxy-peers", peer_relation_id)

    result = TLSRelationService.get_tls_information_from_peer_relation(
        peer_relation, harness.model.app
    )

    assert result is not None
    assert result.hostnames == [hostname]
    assert hostname in result.tls_cert_and_ca_chain
    certificate, chain = result.tls_cert_and_ca_chain[hostname]
    assert str(certificate) == str(mock_certificate)
    assert len(chain) == 1
    assert result.private_key == str(mock_private_key)


def test_get_tls_information_from_peer_relation_empty(
    harness: Harness,
):
    """arrange: Given a peer relation with no certificate data.
    act: Run get_tls_information_from_peer_relation.
    assert: None is returned.
    """
    harness.begin()
    peer_relation_id = harness.add_relation("haproxy-peers", "haproxy")
    peer_relation = harness.model.get_relation("haproxy-peers", peer_relation_id)

    result = TLSRelationService.get_tls_information_from_peer_relation(
        peer_relation, harness.model.app
    )
    assert result is None
