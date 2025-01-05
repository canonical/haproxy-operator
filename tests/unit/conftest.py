# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
import typing
from unittest.mock import MagicMock

import pytest
from charms.tls_certificates_interface.v4.tls_certificates import Certificate, PrivateKey
from ops.testing import Harness

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
def certificates_relation_data_fixture(mock_certificate: str) -> dict[str, str]:
    """Mock tls_certificates relation data."""
    return {
        f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "whatever",
        f"certificate-{TEST_EXTERNAL_HOSTNAME_CONFIG}": mock_certificate,
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
    return certificate, private_key


# @pytest.fixture(scope="function", name="harness_with_mock_certificates_integration")
# def harness_with_mock_certificates_integration_fixture(
#     harness: Harness,
#     certificates_relation_data: dict[str, str],
# ) -> Harness:
#     """Mock certificates integration."""
#     harness.set_leader()
#     harness.update_config({"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
#     relation_id = harness.add_relation(
#         "certificates", "self-signed-certificates", app_data=certificates_relation_data
#     )
#     harness.update_relation_data(
#         relation_id, harness.model.app.name, {f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "csr"}
#     )
#     return harness


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
