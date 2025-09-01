# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for haproxy-operator unit tests."""
import json
import typing
from datetime import timedelta
from ipaddress import IPv4Address
from unittest.mock import MagicMock, Mock, patch

import pytest
import scenario
from charms.haproxy.v1.haproxy_route import RequirerApplicationData, RequirerUnitData
from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    CertificateSigningRequest,
    PrivateKey,
    generate_ca,
    generate_certificate,
    generate_csr,
    generate_private_key,
)
from ops.testing import Context

from charm import HAProxyCharm

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"


@pytest.fixture(scope="function", name="systemd_mock")
def systemd_mock_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock systemd lib methods."""
    monkeypatch.setattr("charms.operator_libs_linux.v1.systemd.service_reload", MagicMock())
    monkeypatch.setattr(
        "charms.operator_libs_linux.v1.systemd.service_running", MagicMock(return_value=True)
    )


@pytest.fixture(scope="function", name="mocks_external_calls")
def mocks_external_calls_fixture(monkeypatch: pytest.MonkeyPatch):
    """Mock external calls."""
    monkeypatch.setattr("haproxy.HAProxyService._validate_haproxy_config", MagicMock())
    monkeypatch.setattr("haproxy.pin_haproxy_package_version", MagicMock())


@pytest.fixture(scope="function", name="ca_certificate_and_key")
def ca_certificate_and_key_fixture() -> typing.Tuple[Certificate, PrivateKey]:
    """Ca Certificate and private key."""
    private_key_ca = generate_private_key()
    ca = generate_ca(generate_private_key(), timedelta(days=10), "caname")
    return ca, private_key_ca


@pytest.fixture(scope="function", name="csr_certificate_and_key")
def csr_certificate_and_key_fixture(
    ca_certificate_and_key,
) -> typing.Tuple[CertificateSigningRequest, Certificate, PrivateKey]:
    """Ca Certificate and private key."""
    ca, private_key_ca = ca_certificate_and_key
    private_key = generate_private_key()
    csr = generate_csr(private_key, TEST_EXTERNAL_HOSTNAME_CONFIG)
    certificate = generate_certificate(csr, ca, private_key_ca, timedelta(days=5))
    return csr, certificate, private_key


@pytest.fixture(scope="function", name="certificates_relation_data")
def certificates_relation_data_fixture(
    csr_certificate_and_key,
    ca_certificate_and_key,
) -> dict[str, str]:
    """Mock tls_certificates relation data."""
    csr, cert, _ = csr_certificate_and_key
    ca_cert, _ = ca_certificate_and_key
    return {
        "certificates": json.dumps(
            [
                {
                    "ca": ca_cert.raw,
                    "certificate_signing_request": csr.raw,
                    "certificate": cert.raw,
                    "chain": [
                        cert.raw,
                        ca_cert.raw,
                    ],
                },
            ]
        )
    }


@pytest.fixture(scope="function", name="mock_certificate_and_key")
def mock_certificate_fixture(
    monkeypatch: pytest.MonkeyPatch,
    csr_certificate_and_key,
) -> typing.Tuple[Certificate, PrivateKey]:
    """Mock tls certificate from a tls provider charm."""
    _, certificate, private_key = csr_certificate_and_key

    provider_cert_mock = MagicMock()
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


@pytest.fixture(scope="function", name="ingress_per_unit_requirer_data")
def ingress_per_unit_requirer_data_fixture() -> dict[str, str]:
    """Mock ingress per unit requirer data."""
    return {
        "model": '"testing"',
        "name": "ingress-requirer/0",
        "host": '"ingress-requirer-0.ingress-requirer-endpoints.testing.svc.cluster.local"',
        "port": "8080",
        "strip-prefix": "true",
    }


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
            (
                install_mock,
                reconcile_default_mock,
                reconcile_ingress_mock,
            ),
        )


@pytest.fixture(name="context_with_reconcile_mock")
def context_with_reconcile_mock_fixture():
    """Context relation fixture.

    Yield: The modeled haproxy-peers relation.
    """
    with (
        patch("haproxy.HAProxyService.reconcile_haproxy_route") as reconcile_mock,
        patch("tls_relation.TLSRelationService.write_certificate_to_unit"),
        patch("charm.HAProxyCharm._get_unit_address") as get_unit_address_mock,
        patch("haproxy.HAProxyService.install"),
    ):
        get_unit_address_mock.return_value = "10.0.0.1"
        yield (
            Context(
                charm_type=HAProxyCharm,
            ),
            reconcile_mock,
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


@pytest.fixture(name="ingress_per_unit_integration")
def ingress_per_unit_integration_fixture(ingress_per_unit_requirer_data):
    """Ingress integration fixture.

    Returns: The modeled ingress integration.
    """
    return scenario.Relation(
        endpoint="ingress-per-unit",
        remote_app_name="requirer",
        remote_units_data={0: ingress_per_unit_requirer_data},
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
def certificates_integration_fixture(certificates_relation_data, csr_certificate_and_key):
    """Certificates integration fixture.

    Returns: The modeled ingress integration.
    """
    csr, _, _ = csr_certificate_and_key
    return scenario.Relation(
        endpoint="certificates",
        remote_app_data=certificates_relation_data,
        local_unit_data={
            "certificate_signing_requests": json.dumps(
                [
                    {
                        "certificate_signing_request": csr.raw,
                        "ca": False,
                    },
                ]
            )
        },
    )


@pytest.fixture(name="receive_ca_certs_relation")
def receive_ca_certs_relation_fixture(ca_certificate_and_key):
    """Receive ca certs relation fixture.

    Args:
        ca_certificate_and_key: The ca certificate for the relation.

    Returns: The modeled relation.
    """
    ca_certificate, _ = ca_certificate_and_key
    return scenario.Relation(
        endpoint="receive-ca-certs",
        interface="certificate_transfer",
        remote_app_name="self-signed-certificates",
        remote_app_data={
            "certificates": json.dumps([ca_certificate.raw]),
            "version": "1",
        },
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


@pytest.fixture(name="haproxy_route_requirer_application_data_with_hosts")
def haproxy_route_requirer_application_data_with_hosts_fixture():
    """haproxy-route requirer application data with hosts attribute set."""
    return RequirerApplicationData(
        service="test-service",
        ports=[8080, 8443],
        hosts=["10.0.0.1", "10.0.0.2"],
        hostname=TEST_EXTERNAL_HOSTNAME_CONFIG,
    ).dump()


@pytest.fixture(name="base_state_haproxy_route")
def base_state_haproxy_route_fixture(
    peer_relation, certificates_integration, haproxy_route_requirer_application_data_with_hosts
):
    """Base state fixture with haproxy-route integration.

    Args:
        peer_relation: peer relation fixture.
        certificates_integration: certificates integration fixture.
        haproxy_route_requirer_application_data_with_hosts: Requirer application data.

    Yield: The modeled haproxy-peers relation.
    """
    input_state = {
        "relations": [
            peer_relation,
            certificates_integration,
            scenario.Relation(
                endpoint="haproxy-route",
                remote_app_name="requirer",
                remote_app_data=haproxy_route_requirer_application_data_with_hosts,
                remote_units_data={0: RequirerUnitData(address=IPv4Address("10.0.0.1")).dump()},
            ),
        ],
        "config": {
            "external-hostname": "haproxy.internal",
        },
    }
    return input_state


@pytest.fixture(name="base_state_with_ingress_per_unit")
def base_state_with_ingress_per_unit_fixture(
    peer_relation, ingress_per_unit_integration, certificates_integration
):
    """Base state fixture with ingress per unit integration.

    Args:
        peer_relation: peer relation fixture.
        ingress_per_unit_integration: ingress per unit integration fixture.
        certificates_integration: certificates integration fixture.

    Yield: The modeled haproxy-peers relation.
    """
    input_state = {
        "relations": [peer_relation, ingress_per_unit_integration, certificates_integration],
        "config": {
            "external-hostname": "ingress.local",
        },
    }
    return input_state


@pytest.fixture(autouse=True)
def mock_out_validate_global_max_conn_check(monkeypatch):
    """Mock out State.validate_global_max_conn.

    This function shells out to `sysctl` which is unnecessary and not
    representative on a machine where unit tests are run.
    """
    monkeypatch.setattr(
        "state.charm_state.check_output", Mock(return_value="fs.file-max = 9223372036854775807")
    )
