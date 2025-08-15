# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route relation tests for haproxy-operator."""

import json
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from charms.tls_certificates_interface.v4 import tls_certificates
from ops.testing import ActiveStatus, Context, Model, Relation, State

from charm import HAProxyCharm

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.fixture
def mocks_external_procceses(monkeypatch: pytest.MonkeyPatch):
    """Mock all external processes calls not relevant for the unit test."""
    monkeypatch.setattr("haproxy.pin_haproxy_package_version", MagicMock())
    monkeypatch.setattr("haproxy.HAProxyService._validate_haproxy_config", MagicMock())


@pytest.fixture
def established_certificate_relation():
    """tls_certificates relation data, with the exchange already produced."""
    csr = tls_certificates.generate_csr(
        tls_certificates.generate_private_key(), TEST_EXTERNAL_HOSTNAME_CONFIG
    )
    private_key_ca = tls_certificates.generate_private_key()
    ca = tls_certificates.generate_ca(
        tls_certificates.generate_private_key(), timedelta(days=10), "caname"
    )
    certificate = tls_certificates.generate_certificate(csr, ca, private_key_ca, timedelta(days=5))
    return Relation(
        endpoint="certificates",
        local_unit_data={
            "certificate_signing_requests": json.dumps(
                [
                    {
                        "certificate_signing_request": csr.raw,
                        "ca": False,
                    }
                ]
            )
        },
        remote_app_data={
            "certificates": json.dumps(
                [
                    {
                        "ca": ca.raw,
                        "certificate_signing_request": csr.raw,
                        "certificate": certificate.raw,
                        "chain": [
                            certificate.raw,
                            ca.raw,
                        ],
                    }
                ]
            ),
        },
    )


@pytest.mark.usefixtures("systemd_mock", "mocks_external_procceses")
def test_protocol_https(monkeypatch: pytest.MonkeyPatch, established_certificate_relation):
    """
    arrange: prepare the state with the haproxy-route relation and protocol https
    act: run relation_changed for the haproxy-route relation
    assert: the unit is active and the the haproxy file was written with ssl and the ca-file
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    # Arrange: prepare the state
    haproxy_route_relation = Relation(
        endpoint="haproxy-route",
        local_app_data={"endpoints": json.dumps([f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"])},
        remote_app_data={
            "hostname": f'"{TEST_EXTERNAL_HOSTNAME_CONFIG}"',
            "hosts": '["10.12.97.153","10.12.97.154"]',
            "ports": "[443]",
            "protocol": '"https"',
            "service": '"haproxy-tutorial-ingress-configurator"',
        },
        remote_units_data={0: {"address": '"10.75.1.129"'}},
    )
    state = State(
        relations=frozenset(
            {
                haproxy_route_relation,
                established_certificate_relation,
            }
        ),
        leader=True,
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    # Act: trigger an event on the state
    ctx = Context(HAProxyCharm, juju_version="3.6.8")

    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )

    render_file_mock.assert_called_once()
    haproxy_conf_contents = render_file_mock.call_args_list[0].args[1]

    assert (
        "server haproxy-tutorial-ingress-configurator_443_0 10.12.97.153:443"
        " ssl ca-file @system-ca\n" in haproxy_conf_contents
    )
    assert (
        "server haproxy-tutorial-ingress-configurator_443_1 10.12.97.154:443"
        " ssl ca-file @system-ca\n" in haproxy_conf_contents
    )
    assert out.app_status == ActiveStatus("")
