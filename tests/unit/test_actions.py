# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the haproxy charm actions."""

import json
from unittest.mock import MagicMock

import ops.testing
import pytest

from charm import HAProxyCharm
from tests.unit.conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.usefixtures("systemd_mock", "mocks_external_calls")
class TestGetProxiedEndpointsAction:
    """Test "get-proxied-endpoints" Action"""

    def test_no_backend_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        arrange: create state with one haproxy-route relation containing
            hostname, additional_hostnames, and paths.
        act: trigger the get-proxied-endpoints action without a backend filter.
        assert: returns a list of all proxied endpoints for every hostname/path combination.
        """
        context = ops.testing.Context(HAProxyCharm)
        render_file_mock = MagicMock()
        monkeypatch.setattr("haproxy.render_file", render_file_mock)
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
            app_status=ops.testing.ActiveStatus(""),
            unit_status=ops.testing.ActiveStatus(""),
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

    def test_no_backend_filter_no_endpoints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        arrange: create state with no haproxy-route relations.
        act: trigger the get-proxied-endpoints action without a backend filter.
        assert: returns an empty list.
        """
        context = ops.testing.Context(HAProxyCharm)
        render_file_mock = MagicMock()
        monkeypatch.setattr("haproxy.render_file", render_file_mock)
        charm_state = ops.testing.State(
            relations=[],
            leader=True,
            model=ops.testing.Model(name="haproxy-tutorial"),
            app_status=ops.testing.ActiveStatus(""),
            unit_status=ops.testing.ActiveStatus(""),
        )
        context.run(context.on.action("get-proxied-endpoints"), charm_state)

        out = context.action_results

        assert out == {"endpoints": "[]"}

    def test_with_backend_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        arrange: create state with a haproxy-route relation for a specific backend.
        act: trigger the get-proxied-endpoints action with the backend filter.
        assert: returns a list containing the endpoint for that backend.
        """
        service_name = "haproxy-tutorial-ingress-configurator"
        context = ops.testing.Context(HAProxyCharm)
        render_file_mock = MagicMock()
        monkeypatch.setattr("haproxy.render_file", render_file_mock)
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
            app_status=ops.testing.ActiveStatus(""),
            unit_status=ops.testing.ActiveStatus(""),
        )
        context.run(
            context.on.action("get-proxied-endpoints", params={"backend": service_name}),
            charm_state,
        )

        out = context.action_results

        assert out == {"endpoints": f'["https://{TEST_EXTERNAL_HOSTNAME_CONFIG}/"]'}

    def test_with_backend_filter_non_existing_backend(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        arrange: create state with a haproxy-route relation for a specific backend.
        act: trigger the get-proxied-endpoints action with a non-existing backend name.
        assert: raises ActionFailed indicating the backend does not exist.
        """
        service_name = "haproxy-tutorial-ingress-configurator"
        context = ops.testing.Context(HAProxyCharm)
        render_file_mock = MagicMock()
        monkeypatch.setattr("haproxy.render_file", render_file_mock)
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
            app_status=ops.testing.ActiveStatus(""),
            unit_status=ops.testing.ActiveStatus(""),
        )
        with pytest.raises(ops.testing.ActionFailed) as excinfo:
            context.run(
                context.on.action("get-proxied-endpoints", params={"backend": "random_name"}),
                charm_state,
            )
        assert str(excinfo.value) == 'No backend with name "random_name"'
