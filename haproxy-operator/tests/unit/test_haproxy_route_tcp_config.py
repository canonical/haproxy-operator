# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario tests for the rendered haproxy-route-tcp configuration."""

import typing
from unittest.mock import MagicMock

import pytest
from ops.testing import Context, State

from charm import HAProxyCharm

from .conftest import build_haproxy_route_tcp_relation


@pytest.mark.parametrize(
    "relation_data,expected_config_entries",
    [
        pytest.param(
            {
                "port": 4444,
                "backend_port": 4000,
                "sni": "example.com",
                "load_balancing": {"algorithm": "source", "consistent_hashing": True},
                "retry": {"count": 3, "redispatch": True},
            },
            [
                "retries 3\n    option redispatch",
                "balance source",
                "hash-type consistent",
            ],
            id="sticky-sessions",
        ),
        pytest.param(
            {
                "port": 4444,
                "backend_port": 4000,
                "sni": "example.com",
                "timeout": {"server": 10, "connect": 5, "queue": 2},
            },
            [
                "timeout server 10s",
                "timeout connect 5s",
                "timeout queue 2s",
            ],
            id="timeouts",
        ),
        pytest.param(
            {
                "port": 4444,
                "backend_port": 4000,
                "sni": "example.com",
                "proxy_protocol": True,
            },
            ["send-proxy-v2"],
            id="proxy-protocol",
        ),
        pytest.param(
            {"port_mapping": "8080-8090:9080-9090"},
            ["bind [::]:8080-8090"],
            id="port-mapping",
        ),
    ],
)
@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls", "mocks_tls_ca_write")
def test_haproxy_route_tcp_config(
    monkeypatch: pytest.MonkeyPatch,
    certificates_integration,
    peer_relation,
    relation_data: dict[str, typing.Any],
    expected_config_entries: list[str],
):
    """
    arrange: Create a haproxy-route-tcp relation with the given configuration.
    act: Trigger the relation changed event.
    assert: The rendered config contains the expected entries.
    """
    render_file_mock = MagicMock()
    monkeypatch.setattr("haproxy.render_file", render_file_mock)
    tcp_relation = build_haproxy_route_tcp_relation(**relation_data)
    state = State(
        relations=frozenset({peer_relation, certificates_integration, tcp_relation}),
        leader=True,
    )
    context = Context(HAProxyCharm, juju_version="3.6.8")
    context.run(context.on.relation_changed(tcp_relation), state)

    render_file_mock.assert_called_once()
    haproxy_config = render_file_mock.call_args_list[0].args[1]
    for entry in expected_config_entries:
        assert entry in haproxy_config
