# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route relation tests for haproxy-operator."""

import json
from unittest.mock import MagicMock

import pytest
from ops.testing import ActiveStatus, Context, Model, Relation, State

from charm import HAProxyCharm

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_protocol_https(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, receive_ca_certs_relation
):
    """
    arrange: prepare the state with the haproxy-route relation and protocol https
    act: run relation_changed for the haproxy-route relation
    assert: the unit is active and the the haproxy file was written with ssl and the ca-file
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
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
                receive_ca_certs_relation,
                haproxy_route_relation,
                certificates_integration,
            }
        ),
        leader=True,
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    ctx = Context(HAProxyCharm, juju_version="3.6.8")
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )

    render_file_mock.assert_called_once()
    haproxy_conf_contents = render_file_mock.call_args_list[0].args[1]
    assert (
        "server haproxy-tutorial-ingress-configurator_443_0 10.12.97.153:443"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2,http/1.1\n" in haproxy_conf_contents
    )
    assert (
        "server haproxy-tutorial-ingress-configurator_443_1 10.12.97.154:443"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2,http/1.1\n" in haproxy_conf_contents
    )
    assert out.app_status == ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
def test_protocol_https_no_ca(monkeypatch: pytest.MonkeyPatch, certificates_integration):
    """
    arrange: prepare the state with the haproxy-route relation and protocol https.
       However, there is no ca-file.
    act: run relation_changed for the haproxy-route relation
    assert: The unit is active, the the data is not in the config file and the relation.
       contains [] which means there is an error.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
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
    haproxy_route_relation_no_https = Relation(
        endpoint="haproxy-route",
        local_app_data={"endpoints": json.dumps([f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"])},
        remote_app_data={
            "hostname": f'"{TEST_EXTERNAL_HOSTNAME_CONFIG}"',
            "hosts": '["10.12.1.2","10.12.1.3"]',
            "ports": "[80]",
            "protocol": '"http"',
            "service": '"haproxy-tutorial-ingress-http-configurator"',
        },
        remote_units_data={0: {"address": '"10.75.1.4"'}},
    )
    state = State(
        relations=frozenset(
            {
                haproxy_route_relation,
                haproxy_route_relation_no_https,
                certificates_integration,
            }
        ),
        leader=True,
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    ctx = Context(HAProxyCharm, juju_version="3.6.8")
    out = ctx.run(
        ctx.on.relation_changed(haproxy_route_relation),
        state,
    )

    render_file_mock.assert_called_once()
    haproxy_conf_contents = render_file_mock.call_args_list[0].args[1]
    assert "10.12.97.153:443" not in haproxy_conf_contents
    assert "10.12.97.154:443" not in haproxy_conf_contents
    protocol_https_relation = next(
        rel
        for rel in out.relations
        if rel.endpoint == "haproxy-route" and rel.remote_app_data["protocol"] == '"https"'
    )
    # The relation data is invalid
    assert protocol_https_relation.local_app_data["endpoints"] == "[]"  # type: ignore
    assert out.app_status == ActiveStatus("")
