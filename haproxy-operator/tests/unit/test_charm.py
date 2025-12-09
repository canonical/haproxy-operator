# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the haproxy charm."""

import json
import logging
import pathlib
import re
from unittest.mock import ANY, MagicMock

import ops
import ops.testing
import pytest
import scenario

import tls_relation
from charm import HAProxyCharm
from tests.unit.conftest import TEST_EXTERNAL_HOSTNAME_CONFIG

from .conftest import build_haproxy_route_relation, build_spoe_auth_relation
from .helper import RegexMatcher

logger = logging.getLogger(__name__)


def test_install(context_with_install_mock, base_state):
    """
    arrange: prepare some state with peer relation
    act: run start
    assert: status is active
    """
    context, (install_mock, reconcile_default_mock, *_) = context_with_install_mock
    state = ops.testing.State(**base_state)
    context.run(context.on.install(), state)
    install_mock.assert_called_once()
    reconcile_default_mock.assert_called_once()


def test_ingress_per_unit_mode_success(
    context_with_install_mock, base_state_with_ingress_per_unit
):
    """
    arrange: prepare some state with ingress per unit relation
    act: trigger config changed hook
    assert: reconcile_ingress is called once
    """
    context, (*_, reconcile_ingress_mock) = context_with_install_mock
    state = ops.testing.State(**base_state_with_ingress_per_unit)
    context.run(context.on.config_changed(), state)
    reconcile_ingress_mock.assert_called_once()


def test_ingress_per_unit_data_validation_error(
    context_with_install_mock, base_state_with_ingress_per_unit
):
    """
    arrange: prepare some state with ingress per unit relation
    act: trigger config changed hook
    assert: haproxy is in a blocked state
    """
    context, _ = context_with_install_mock
    base_state_with_ingress_per_unit["relations"][1] = scenario.Relation(
        endpoint="ingress-per-unit", remote_app_name="requirer", remote_units_data={0: {}}
    )
    state = ops.testing.State(**base_state_with_ingress_per_unit)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.testing.BlockedStatus(
        "Validation of ingress per unit relation data failed."
    )


def test_ingress_mode_success(context_with_install_mock, base_state_with_ingress):
    """
    arrange: prepare some state with ingress relation
    act: trigger config changed hook
    assert: reconcile ingress is called once
    """
    context, (*_, reconcile_ingress_mock) = context_with_install_mock
    state = ops.testing.State(**base_state_with_ingress)
    context.run(context.on.config_changed(), state)
    reconcile_ingress_mock.assert_called_once()


def test_ingress_data_validation_error(context_with_install_mock, base_state_with_ingress):
    """
    arrange: prepare some state with ingress relation
    act: trigger config changed hook
    assert: haproxy is in a blocked state
    """
    context, _ = context_with_install_mock
    base_state_with_ingress["relations"][1] = scenario.Relation(
        endpoint="ingress", remote_app_name="requirer", remote_app_data={}
    )
    state = ops.testing.State(**base_state_with_ingress)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.testing.BlockedStatus(
        "Validation of ingress relation data failed."
    )


def test_haproxy_route(context_with_reconcile_mock, base_state_haproxy_route):
    """
    arrange: prepare some state with peer relation
    act: run start
    assert: status is active
    """
    context, reconcile_mock = context_with_reconcile_mock
    state = ops.testing.State(**base_state_haproxy_route)
    context.run(context.on.config_changed(), state)
    reconcile_mock.assert_called_once()


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ca_certificates_available(
    monkeypatch: pytest.MonkeyPatch, receive_ca_certs_relation, ca_certificate_and_key
):
    """
    arrange: Prepare a state with the receive-ca-cert.
    act: Run relation_changed for the receive-ca-cert relation.
    assert: The unit is active and the certificate in the relation was written to the file.
    """
    ca_certificate, _ = ca_certificate_and_key
    render_file_mock = MagicMock()
    monkeypatch.setattr("tls_relation.render_file", render_file_mock)
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    mock_cas_dir = MagicMock()
    mock_cas_dir.exists.return_value = False
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_DIR", mock_cas_dir)

    state = ops.testing.State(
        relations=frozenset({receive_ca_certs_relation}),
        leader=True,
        model=ops.testing.Model(name="haproxy-tutorial"),
        app_status=ops.testing.ActiveStatus(""),
        unit_status=ops.testing.ActiveStatus(""),
    )

    ctx = ops.testing.Context(HAProxyCharm)
    out = ctx.run(
        ctx.on.relation_changed(receive_ca_certs_relation),
        state,
    )
    mock_cas_dir.mkdir.assert_called_once()
    render_file_mock.assert_any_call(
        tls_relation.HAPROXY_CAS_FILE, ca_certificate.raw + "\n", 0o644
    )
    assert out.app_status == ops.testing.ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_ca_certificates_removed(monkeypatch: pytest.MonkeyPatch, receive_ca_certs_relation):
    """
    arrange: Prepare a state with the receive-ca-cert and the external accesses mocked.
    act: Run relation_broken for the receive-ca-cert relation.
    assert: The CA certificates file is removed from the unit.
    """
    monkeypatch.setattr("haproxy.render_file", MagicMock())

    mock_cas_file = MagicMock()
    monkeypatch.setattr("tls_relation.HAPROXY_CAS_FILE", mock_cas_file)

    state = ops.testing.State(
        relations=frozenset({receive_ca_certs_relation}),
        model=ops.testing.Model(name="haproxy-tutorial"),
        app_status=ops.testing.ActiveStatus(""),
        unit_status=ops.testing.ActiveStatus(""),
    )

    ctx = ops.testing.Context(HAProxyCharm)
    out = ctx.run(
        ctx.on.relation_broken(receive_ca_certs_relation),
        state,
    )

    mock_cas_file.unlink.assert_called_once()
    assert out.app_status == ops.testing.ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
class TestGetProxiedEndpointsAction:
    """Test "get-proxied-endpoints" Action"""

    def test_no_backend_filter(self) -> None:
        """
        arrange: create state with one haproxy-route relation containing
            hostname, additional_hostnames, and paths.
        act: trigger the get-proxied-endpoints action without a backend filter.
        assert: returns a list of all proxied endpoints for every hostname/path combination.
        """
        context = ops.testing.Context(HAProxyCharm)

        haproxy_route_relation = ops.testing.Relation(
            "haproxy-route",
            remote_app_data={
                "hostname": f'"{TEST_EXTERNAL_HOSTNAME_CONFIG}"',
                "additional_hostnames": json.dumps(
                    [
                        f"ok2.{TEST_EXTERNAL_HOSTNAME_CONFIG}",
                        f"ok3.{TEST_EXTERNAL_HOSTNAME_CONFIG}",
                    ]
                ),
                "paths": '["v1", "v2"]',
                "ports": "[443]",
                "protocol": '"http"',
                "service": '"haproxy-tutorial-ingress-configurator"',
            },
            remote_units_data={0: {"address": '"10.75.1.129"'}},
        )
        charm_state = ops.testing.State(
            relations=[haproxy_route_relation],
            leader=True,
            model=ops.testing.Model(name="haproxy-tutorial"),
            app_status=ops.testing.ActiveStatus(),
            unit_status=ops.testing.ActiveStatus(),
        )
        context.run(context.on.action("get-proxied-endpoints"), charm_state)

        out = context.action_results

        assert out == {
            "endpoints": json.dumps(
                [
                    "https://haproxy.internal/v1",
                    "https://haproxy.internal/v2",
                    "https://ok2.haproxy.internal/v1",
                    "https://ok2.haproxy.internal/v2",
                    "https://ok3.haproxy.internal/v1",
                    "https://ok3.haproxy.internal/v2",
                ]
            )
        }

    def test_no_backend_filter_no_endpoints(self) -> None:
        """
        arrange: create state with no haproxy-route relations.
        act: trigger the get-proxied-endpoints action without a backend filter.
        assert: returns an empty list.
        """
        context = ops.testing.Context(HAProxyCharm)
        charm_state = ops.testing.State(
            relations=[],
            leader=True,
            model=ops.testing.Model(name="haproxy-tutorial"),
            app_status=ops.testing.ActiveStatus(),
            unit_status=ops.testing.ActiveStatus(),
        )
        context.run(context.on.action("get-proxied-endpoints"), charm_state)

        out = context.action_results

        assert out == {"endpoints": "[]"}

    def test_with_backend_filter(self) -> None:
        """
        arrange: create state with a haproxy-route relation for a specific backend.
        act: trigger the get-proxied-endpoints action with the backend filter.
        assert: returns a list containing the endpoint for that backend.
        """
        service_name = "haproxy-tutorial-ingress-configurator"
        context = ops.testing.Context(HAProxyCharm)
        haproxy_route_relation = ops.testing.Relation(
            "haproxy-route",
            remote_app_data={
                "hostname": f'"{TEST_EXTERNAL_HOSTNAME_CONFIG}"',
                "ports": "[443]",
                "protocol": '"http"',
                "service": f'"{service_name}"',
            },
            remote_units_data={0: {"address": '"10.75.1.129"'}},
        )
        charm_state = ops.testing.State(
            relations=[haproxy_route_relation],
            leader=True,
            model=ops.testing.Model(name="haproxy-tutorial"),
            app_status=ops.testing.ActiveStatus(),
            unit_status=ops.testing.ActiveStatus(),
        )
        context.run(
            context.on.action("get-proxied-endpoints", params={"backend": service_name}),
            charm_state,
        )

        out = context.action_results

        assert out == {"endpoints": f'["https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"]'}

    def test_with_backend_filter_non_existing_backend(self) -> None:
        """
        arrange: create state with a haproxy-route relation for a specific backend.
        act: trigger the get-proxied-endpoints action with a non-existing backend name.
        assert: raises ActionFailed indicating the backend does not exist.
        """
        service_name = "haproxy-tutorial-ingress-configurator"
        context = ops.testing.Context(HAProxyCharm)
        haproxy_route_relation = ops.testing.Relation(
            "haproxy-route",
            remote_app_data={
                "hostname": f'"{TEST_EXTERNAL_HOSTNAME_CONFIG}"',
                "ports": "[443]",
                "protocol": '"http"',
                "service": f'"{service_name}"',
            },
            remote_units_data={0: {"address": '"10.75.1.129"'}},
        )
        charm_state = ops.testing.State(
            relations=[haproxy_route_relation],
            leader=True,
            model=ops.testing.Model(name="haproxy-tutorial"),
            app_status=ops.testing.ActiveStatus(),
            unit_status=ops.testing.ActiveStatus(),
        )

        context.run(
            context.on.action("get-proxied-endpoints", params={"backend": "random_name"}),
            charm_state,
        )

        out = context.action_results

        assert out == {"endpoints": "[]"}


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_spoe_auth(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route and spoe.
    act: trigger relation changed.
    assert: The haproxy.conf and spoe_auth.conf files are writtern with the relevant lines.
    """
    monkeypatch.setattr(
        "charms.tls_certificates_interface.v4.tls_certificates.TLSCertificatesRequiresV4.private_key",
        MagicMock(),
    )
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    spoe_auth_relation = build_spoe_auth_relation()
    haproxy_route_relation = build_haproxy_route_relation()

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, spoe_auth_relation, haproxy_route_relation]
    )
    out = ctx.run(
        ctx.on.relation_changed(spoe_auth_relation),
        state,
    )
    assert render_file_mock.call_count == 2
    # It should write the files:
    # - /etc/haproxy/spoe_auth.conf
    # - /etc/haproxy/haproxy.cfg
    # Test a random line related to spoe-auth in each file.
    render_file_mock.assert_any_call(
        pathlib.Path("/etc/haproxy/spoe_auth.conf"),
        RegexMatcher("event on-frontend-http-request"),
        ANY,
    )
    render_file_mock.assert_any_call(
        pathlib.Path("/etc/haproxy/haproxy.cfg"),
        RegexMatcher("filter spoe engine spoe-auth"),
        ANY,
    )
    assert out.unit_status == ops.testing.ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_two_spoe_auth(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: are a haproxy with two haproxy_route and two spoe.
    act: trigger relation changed.
    assert: The haproxy.conf and spoe_auth.conf files are writtern with the relevant lines.
    """
    monkeypatch.setattr(
        "charms.tls_certificates_interface.v4.tls_certificates.TLSCertificatesRequiresV4.private_key",
        MagicMock(),
    )
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    spoe_auth_relation_1 = build_spoe_auth_relation(hostname="haproxy1.internal")
    haproxy_route_relation_1 = build_haproxy_route_relation(
        hostname="haproxy1.internal", service="service1"
    )
    spoe_auth_relation_2 = build_spoe_auth_relation(hostname="haproxy2.internal")
    haproxy_route_relation_2 = build_haproxy_route_relation(
        hostname="haproxy2.internal", service="service2"
    )

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[
            certificates_integration,
            spoe_auth_relation_1,
            spoe_auth_relation_2,
            haproxy_route_relation_1,
            haproxy_route_relation_2,
        ]
    )
    out = ctx.run(
        ctx.on.relation_changed(spoe_auth_relation_1),
        state,
    )
    assert render_file_mock.call_count == 2
    # It should write the files:
    # - /etc/haproxy/spoe_auth.conf
    # - /etc/haproxy/haproxy.cfg
    # assert some required information in the files for each relation.
    spoe_rel_ids = {rel.id for rel in out.relations if rel.endpoint == "spoe-auth"}
    for rel in spoe_rel_ids:
        render_file_mock.assert_any_call(
            pathlib.Path("/etc/haproxy/spoe_auth.conf"),
            RegexMatcher(re.escape(f"[spoe-auth-{rel}]")),
            ANY,
        )
        render_file_mock.assert_any_call(
            pathlib.Path("/etc/haproxy/haproxy.cfg"),
            RegexMatcher(
                re.escape(f"filter spoe engine spoe-auth-{rel} config /etc/haproxy/spoe_auth.conf")
            ),
            ANY,
        )
    assert out.unit_status == ops.testing.ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_spoe_auth_invalid_data(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: Prepare a haproxy with haproxy_route and spoe with wrong data in the spoe-auth relation.
    act: trigger relation changed.
    assert: No file should be updated and the charm should be blocked.
    """
    monkeypatch.setattr(
        "charms.tls_certificates_interface.v4.tls_certificates.TLSCertificatesRequiresV4.private_key",
        MagicMock(),
    )
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)

    spoe_auth_relation = build_spoe_auth_relation()
    del spoe_auth_relation.remote_app_data["hostname"]
    haproxy_route_relation = build_haproxy_route_relation()

    ctx = ops.testing.Context(HAProxyCharm)
    state = ops.testing.State(
        relations=[certificates_integration, spoe_auth_relation, haproxy_route_relation]
    )
    out = ctx.run(
        ctx.on.relation_changed(spoe_auth_relation),
        state,
    )
    assert render_file_mock.call_count == 0
    assert out.unit_status == ops.testing.BlockedStatus("")
