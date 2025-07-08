# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
import typing
from unittest.mock import MagicMock, patch

import pytest
import scenario
from charms.tls_certificates_interface.v4.tls_certificates import Certificate, PrivateKey
from ops.testing import Context, Harness

from charm import HAProxyCharm

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"


@pytest.fixture(scope="function", name="harness")
def harness_fixture():
    """Enable ops test framework harness."""
    harness = Harness(HAProxyCharm)
    yield harness
    harness.cleanup()


@pytest.fixture(scope="function", name="systemd_mock")
def systemd_mock_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock systemd lib methods."""
    monkeypatch.setattr("charms.operator_libs_linux.v1.systemd.service_reload", MagicMock())
    monkeypatch.setattr(
        "charms.operator_libs_linux.v1.systemd.service_running", MagicMock(return_value=True)
    )


@pytest.fixture(scope="function", name="certificates_relation_data")
def certificates_relation_data_fixture(
    mock_certificate_and_key: typing.Tuple[Certificate, PrivateKey],
) -> dict[str, str]:
    """Mock tls_certificates relation data."""
    cert, _ = mock_certificate_and_key
    return {
        f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
        f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}": str(cert),
        f"ca-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
        f"chain-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
    }


@pytest.fixture(scope="function", name="mock_certificate_and_key")
def mock_certificate_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> typing.Tuple[Certificate, PrivateKey]:
    """Mock tls certificate from a tls provider charm."""
    with open("tests/unit/cert.pem", encoding="utf-8") as f:
        cert = f.read()
    with open("tests/unit/key.pem", encoding="utf-8") as f:
        key = f.read()

    provider_cert_mock = MagicMock()
    private_key = PrivateKey.from_string(key)
    certificate = Certificate.from_string(cert)
    provider_cert_mock.certificate = certificate
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v4.tls_certificates"
            ".TLSCertificatesRequiresV4.get_assigned_certificate"
        ),
        MagicMock(return_value=(provider_cert_mock, private_key)),
    )
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v4.tls_certificates"
            ".TLSCertificatesRequiresV4.get_assigned_certificates"
        ),
        MagicMock(return_value=([provider_cert_mock], private_key)),
    )
    return certificate, private_key


@pytest.fixture(scope="function", name="ingress_requirer_application_data")
def ingress_requirer_application_data_fixture() -> dict[str, str]:
    """Mock ingress requirer application data."""
    return {
        "name": '"ingress_requirer"',
        "model": '"testing"',
        "port": "8080",
        "strip_prefix": "false",
        "redirect_https": "false",
    }


@pytest.fixture(scope="function", name="ingress_requirer_unit_data")
def ingress_requirer_unit_data_fixture() -> dict[str, str]:
    """Mock ingress requirer unit data."""
    return {"host": '"testing.ingress"', "ip": '"10.0.0.1"'}


# Scenario
@pytest.fixture(name="context_with_install_mock")
def context_with_install_mock_fixture():
    """Context relation fixture.

    Yield: The modeled haproxy-peers relation.
    """
    with (
        patch("haproxy.HAProxyService.install") as install_mock,
        patch("haproxy.HAProxyService.reconcile_default") as reconcile_default_mock,
        patch("haproxy.HAProxyService.reconcile_ingress") as reconcile_ingress_mock,
        patch("tls_relation.TLSRelationService.write_certificate_to_unit"),
    ):
        yield (
            Context(
                charm_type=HAProxyCharm,
            ),
            (install_mock, reconcile_default_mock, reconcile_ingress_mock),
        )


@pytest.fixture(name="peer_relation")
def peer_relation_fixture():
    """Peer relation fixture.

    Yield: The modeled haproxy-peers relation.
    """
    return scenario.PeerRelation(
        endpoint="haproxy-peers",
        peers_data={},
    )


@pytest.fixture(name="ingress_integration")
def ingress_integration_fixture(ingress_requirer_application_data, ingress_requirer_unit_data):
    """Ingress integration fixture.

    Returns: The modeled ingress integration.
    """
    return scenario.Relation(
        endpoint="ingress",
        remote_app_name="requirer",
        remote_app_data=ingress_requirer_application_data,
        remote_units_data={0: ingress_requirer_unit_data},
    )


@pytest.fixture(name="certificates_integration")
def certificates_integration_fixture(certificates_relation_data):
    """Certificates integration fixture.

    Returns: The modeled ingress integration.
    """
    return scenario.Relation(
        endpoint="certificates",
        remote_app_name="provider",
        remote_app_data=certificates_relation_data,
    )


@pytest.fixture(name="base_state")
def base_state_fixture(peer_relation):
    """Base state fixture.

    Args:
        peer_relation: peer relation fixture

    Yield: The modeled haproxy-peers relation.
    """
    input_state = {
        "relations": [peer_relation],
    }
    return input_state


@pytest.fixture(name="base_state_with_ingress")
def base_state_with_ingress_fixture(peer_relation, ingress_integration, certificates_integration):
    """Base state fixture with ingress integration.

    Args:
        peer_relation: peer relation fixture.
        ingress_integration: ingress integration fixture.
        certificates_integration: certificates integration fixture.

    Yield: The modeled haproxy-peers relation.
    """
    input_state = {
        "relations": [peer_relation, ingress_integration, certificates_integration],
        "config": {
            "external-hostname": "ingress.local",
        },
    }
    return input_state
