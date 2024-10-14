# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
from unittest.mock import MagicMock

import pytest
from ops.model import Secret
from ops.testing import Harness

from charm import HAProxyCharm
from tls_relation import TLSRelationService, generate_private_key

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


@pytest.fixture(scope="function", name="private_key_and_password")
def private_key_and_password_fixture(harness: Harness) -> tuple[str, str]:
    """Mock private key juju secret."""
    tls = TLSRelationService(harness.model, MagicMock())
    password = tls.generate_password().encode()
    private_key = generate_private_key(password=password)
    return (password.decode(), private_key.decode())


@pytest.fixture(scope="function", name="mock_certificate")
def mock_certificate_fixture(monkeypatch: pytest.MonkeyPatch) -> str:
    """Mock tls certificate from a tls provider charm."""
    cert = (
        "-----BEGIN CERTIFICATE-----"
        "MIIDgDCCAmigAwIBAgIUbKlLu3PxWNcLKePoKoq21y7bcCkwDQYJKoZIhvcNAQEL"
        "BQAwOTELMAkGA1UEBhMCVVMxKjAoBgNVBAMMIXNlbGYtc2lnbmVkLWNlcnRpZmlj"
        "YXRlcy1vcGVyYXRvcjAeFw0yNDA4MTIxOTA0MDBaFw0yNTA4MTIxOTA0MDBaMEox"
        "GTAXBgNVBAMMEGhhcHJveHkuaW50ZXJuYWwxLTArBgNVBC0MJDQxYWE2YmE0LWI3"
        "ZjktNGJmMy1iYTJhLTk1YWZhYTQ3ZDJkMzCCASIwDQYJKoZIhvcNAQEBBQADggEP"
        "ADCCAQoCggEBALFq15bjeRJlhVDRmUFJk7V7gwFSzYPhcLaGy8UHZpznxKIdZ2bQ"
        "wnQgpbSPdt7mFK9uyKWBpj+hCfPcoPkg+3XWlEQm5o/HzN08lp2gC+1KBzx/mdDd"
        "fDYy1Uv/EyeeubI8UEofKXN4RZ5PHuSBnjb8548XiS1WPuFL80qUCWnIgvm2otUX"
        "BEddSNEi+xUCjdSLk6zzIYzZ0CHUr7LziX2DFi/JbklJEl7YmHqMoz9BP3n/Xt9A"
        "yjN9yi4jxPBoNrXAP+DuBXL2bq3EyD7CKTlsd8pe1HtobyL+3cw5vAhdkBjiM3uI"
        "8PdbGibmNZI36j6GoihJdRVmH76Ix6oRthkCAwEAAaNvMG0wIQYDVR0jBBowGIAW"
        "BBR2ca55yP746dDO1L3w/lSsKAi60DAdBgNVHQ4EFgQUY5Ou1cim6db0e+Va95VH"
        "ZC9jn/MwDAYDVR0TAQH/BAIwADAbBgNVHREEFDASghBoYXByb3h5LmludGVybmFs"
        "MA0GCSqGSIb3DQEBCwUAA4IBAQAO7oiD4X4D17VuHGwJJO6WmhBzRNV8ff9p/6fq"
        "NhbdA8IylzGLZ0PRld8o6rVbYNs2ufvz14cQxZaO5GqOxl4KufjapRxbxdEN7Pr1"
        "wLavXGoMzpCtwLhW5B0qxA+DDoTB7KEGaNxe49dkm4JDMrTxaa29QV3rOH6+zKH3"
        "vHfmBbx27xaPDgoQUfbTFt5tG32j7HnMCh/s/+0l+deUSFIsaz/3yopLpScgUXuy"
        "+0rhQ3KFsp9dxfhvpip6BHZwoPGzD8NVAmbkSQ6G8SXIxcAxwtayczsGm9tdygc8"
        "Dhahajgpkum+TaLU2o6PXIawuE1tvux7BvELWx1VS61LSa31"
        "-----END CERTIFICATE-----"
    )
    provider_cert_mock = MagicMock()
    provider_cert_mock.certificate = cert
    monkeypatch.setattr(
        (
            "charms.tls_certificates_interface.v3.tls_certificates"
            ".TLSCertificatesRequiresV3.get_provider_certificates"
        ),
        MagicMock(return_value=[provider_cert_mock]),
    )
    return cert


@pytest.fixture(scope="function", name="juju_secret_mock")
def juju_secret_mock_fixture(
    monkeypatch: pytest.MonkeyPatch,
    private_key_and_password: tuple[str, str],
) -> tuple[str, str]:
    """Mock certificates integration."""
    password, private_key = private_key_and_password
    juju_secret_mock = MagicMock(spec=Secret)
    juju_secret_mock.get_content.return_value = {"key": private_key, "password": password}
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(return_value=juju_secret_mock))
    return juju_secret_mock


@pytest.fixture(scope="function", name="harness_with_mock_certificates_integration")
def harness_with_mock_certificates_integration_fixture(
    harness: Harness,
    certificates_relation_data: dict[str, str],
) -> Harness:
    """Mock certificates integration."""
    harness.set_leader()
    harness.update_config({"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    relation_id = harness.add_relation(
        "certificates", "self-signed-certificates", app_data=certificates_relation_data
    )
    harness.update_relation_data(
        relation_id, harness.model.app.name, {f"csr-{TEST_EXTERNAL_HOSTNAME_CONFIG}": "csr"}
    )
    return harness


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
