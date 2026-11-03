# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route relation tests for haproxy-operator."""

import json
from unittest.mock import MagicMock

import pytest
from ops.testing import ActiveStatus, Context, Model, Relation, State

from charm import HAProxyCharm

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
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
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2,http/1.1 check-alpn h2,http/1.1\n"
        in haproxy_conf_contents
    )
    assert (
        "server haproxy-tutorial-ingress-configurator_443_1 10.12.97.154:443"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2,http/1.1 check-alpn h2,http/1.1\n"
        in haproxy_conf_contents
    )
    assert "option forwardfor" in haproxy_conf_contents
    assert (
        "http-request set-header X-Forwarded-Proto %[ssl_fc,iif(https,http)]"
        in haproxy_conf_contents
    )
    assert out.app_status == ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_protocol_https_with_health_check(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, receive_ca_certs_relation
):
    """
    arrange: prepare the state with the haproxy-route relation, protocol https, and health checks
    act: run relation_changed for the haproxy-route relation
    assert: the server line contains check-alpn h2,http/1.1 alongside alpn h2,http/1.1
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
            "check": '{"interval": 60, "rise": 2, "fall": 1, "path": "/sys/health"}',
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
        " check inter 60s rise 2 fall 1"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2,http/1.1 check-alpn h2,http/1.1\n"
        in haproxy_conf_contents
    )
    assert (
        "server haproxy-tutorial-ingress-configurator_443_1 10.12.97.154:443"
        " check inter 60s rise 2 fall 1"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2,http/1.1 check-alpn h2,http/1.1\n"
        in haproxy_conf_contents
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
        if rel.endpoint == "haproxy-route" and rel.remote_app_data["protocol"] == '"https"'  # type: ignore[attr-defined]
    )
    # The relation data is invalid
    assert protocol_https_relation.local_app_data["endpoints"] == "[]"  # type: ignore
    assert out.app_status == ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_grpc_backend(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, receive_ca_certs_relation
):
    """
    arrange: prepare the state with the haproxy-route relation with external_grpc_port and
        protocol https.
    act: run relation_changed for the haproxy-route relation.
    assert: the rendered config contains the gRPC server line with ssl ca-file, alpn h2,
        and check-alpn h2.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    haproxy_route_relation = Relation(
        endpoint="haproxy-route",
        local_app_data={"endpoints": json.dumps([f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"])},
        remote_app_data={
            "hostname": f'"{TEST_EXTERNAL_HOSTNAME_CONFIG}"',
            "hosts": '["10.12.97.153","10.12.97.154"]',
            "ports": "[50051]",
            "protocol": '"https"',
            "service": '"grpc-service"',
            "external_grpc_port": "9090",
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
        "server grpc-service_50051_0 10.12.97.153:50051"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2 check-alpn h2\n"
        in haproxy_conf_contents
    )
    assert (
        "server grpc-service_50051_1 10.12.97.154:50051"
        " ssl ca-file /var/lib/haproxy/cas/cas.pem alpn h2 check-alpn h2\n"
        in haproxy_conf_contents
    )
    assert out.app_status == ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
@pytest.mark.parametrize("include_regular_backend", [False, True])
def test_default_backend_renders_default_backend_directive(
    monkeypatch: pytest.MonkeyPatch,
    certificates_integration,
    receive_ca_certs_relation,
    include_regular_backend,
):
    """
    arrange: prepare the state with a default backend and optionally a regular backend.
    act: run relation_changed for the haproxy-route relation.
    assert: the HTTP frontend targets the default backend without ACLs or use_backend,
        and renders its backend configuration exactly once.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    regular_relation = Relation(
        endpoint="haproxy-route",
        id=1,
        local_app_data={"endpoints": json.dumps([f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"])},
        remote_app_data={
            "hostname": '"regular.example.com"',
            "hosts": '["10.12.97.153"]',
            "ports": "[80]",
            "service": '"regular-service"',
        },
        remote_units_data={0: {"address": '"10.75.1.129"'}},
    )
    default_relation = Relation(
        endpoint="haproxy-route",
        id=2,
        local_app_data={"endpoints": json.dumps([f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"])},
        remote_app_data={
            "hostname": '"landing.example.com"',
            "hosts": '["10.12.97.154"]',
            "ports": "[80]",
            "service": '"default-service"',
            "default_backend": "true",
            "paths": '["/landing"]',
            "deny_paths": '["/private"]',
            "check": '{"interval": 10, "rise": 2, "fall": 3, "path": "/health"}',
            "timeout": '{"server": 30, "connect": 5, "queue": 15}',
            "load_balancing": '{"algorithm": "roundrobin"}',
            "rate_limit": '{"connections_per_minute": 100}',
            "rewrites": '[{"method": "set-path", "expression": "/welcome"}]',
        },
        remote_units_data={0: {"address": '"10.75.1.130"'}},
    )
    state = State(
        relations=frozenset(
            {
                certificates_integration,
                receive_ca_certs_relation,
                default_relation,
            }
            | ({regular_relation} if include_regular_backend else set())
        ),
        leader=True,
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    ctx = Context(HAProxyCharm, juju_version="3.6.8")
    out = ctx.run(
        ctx.on.relation_changed(default_relation),
        state,
    )

    render_file_mock.assert_called_once()
    haproxy_conf_contents = render_file_mock.call_args_list[0].args[1]
    assert "frontend haproxy\n" in haproxy_conf_contents
    assert "bind [::]:80 v4v6" in haproxy_conf_contents
    assert "bind [::]:443 v4v6 ssl" in haproxy_conf_contents
    assert "default_backend default-service\n" in haproxy_conf_contents
    assert "default_backend default\n" not in haproxy_conf_contents
    assert "backend default\n" not in haproxy_conf_contents
    assert "acl_host_default-service" not in haproxy_conf_contents
    assert "acl_path_default-service" not in haproxy_conf_contents
    assert "acl_deny_path_default-service" not in haproxy_conf_contents
    assert "use_backend default-service" not in haproxy_conf_contents
    assert ("acl_host_regular-service" in haproxy_conf_contents) is include_regular_backend
    assert ("use_backend regular-service" in haproxy_conf_contents) is include_regular_backend
    assert haproxy_conf_contents.count("\nbackend default-service\n") == 1
    default_backend_config = haproxy_conf_contents.split("\nbackend default-service\n")[1]
    assert "balance roundrobin\n" in default_backend_config
    assert "timeout server 30s\n" in default_backend_config
    assert "timeout connect 5s\n" in default_backend_config
    assert "timeout queue 15s\n" in default_backend_config
    assert "option httpchk GET /health\n" in default_backend_config
    assert "table default-service_rate_limit" in haproxy_conf_contents
    assert "http-request track-sc0 src table  haproxy_peers/default-service_rate_limit" in (
        default_backend_config
    )
    assert "http-request set-path /welcome\n" in default_backend_config
    assert "server default-service_80_0 10.12.97.154:80 check inter 10s rise 2 fall 3" in (
        default_backend_config
    )
    assert out.app_status == ActiveStatus("")


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_no_default_backend_renders_inline_default(
    monkeypatch: pytest.MonkeyPatch, certificates_integration, receive_ca_certs_relation
):
    """
    arrange: prepare the state with a single regular backend.
    act: run relation_changed for the haproxy-route relation.
    assert: the inline default backend is used as the default_backend target.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    regular_relation = Relation(
        endpoint="haproxy-route",
        local_app_data={"endpoints": json.dumps([f"https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"])},
        remote_app_data={
            "hostname": '"regular.example.com"',
            "hosts": '["10.12.97.153"]',
            "ports": "[80]",
            "service": '"regular-service"',
        },
        remote_units_data={0: {"address": '"10.75.1.129"'}},
    )
    state = State(
        relations=frozenset(
            {
                certificates_integration,
                receive_ca_certs_relation,
                regular_relation,
            }
        ),
        leader=True,
        model=Model(name="haproxy-tutorial"),
        app_status=ActiveStatus(""),
        unit_status=ActiveStatus(""),
    )

    ctx = Context(HAProxyCharm, juju_version="3.6.8")
    out = ctx.run(
        ctx.on.relation_changed(regular_relation),
        state,
    )

    render_file_mock.assert_called_once()
    haproxy_conf_contents = render_file_mock.call_args_list[0].args[1]
    assert "default_backend default\n" in haproxy_conf_contents
    assert "backend default\n" in haproxy_conf_contents
    assert out.app_status == ActiveStatus("")
