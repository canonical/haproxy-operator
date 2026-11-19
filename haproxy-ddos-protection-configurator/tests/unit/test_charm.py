# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json

import ops
import pytest
from ops import testing

from charm import HAProxyDDoSProtectionConfiguratorCharm


def test_charm_starts_successfully():
    """
    arrange: Create a charm context.
    act: Run the start event.
    assert: Unit status is ActiveStatus.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(leader=True)
    out = ctx.run(ctx.on.start(), state)
    assert out.unit_status == testing.ActiveStatus()


def test_config_changed_with_valid_config():
    """
    arrange: Create a charm context with complete valid DDoS protection configuration.
    act: Run the config-changed event.
    assert: Unit status is ActiveStatus.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(
        leader=True,
        config={
            "rate-limit-requests-per-minute": 100,
            "rate-limit-connections-per-minute": 50,
            "concurrent-connections-limit": 1000,
            "error-rate-per-minute": 10,
            "limit-policy-http": "reject",
            "limit-policy-tcp": "reject",
            "ip-allow-list": "192.168.1.1, 192.168.1.0/24",
            "http-request-timeout": 30,
            "http-keepalive-timeout": 60,
            "client-timeout": 50,
            "deny-paths": "/admin, /internal",
        },
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert out.unit_status == testing.ActiveStatus()


def test_config_changed_with_invalid_rate_limit_requests():
    """
    arrange: Create a charm context with negative rate-limit-requests-per-minute.
    act: Run the config-changed event.
    assert: Unit status is BlockedStatus.
    """
    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    state = testing.State(
        leader=True,
        config={
            "rate-limit-requests-per-minute": -100,
        },
    )
    out = ctx.run(ctx.on.config_changed(), state)
    assert isinstance(out.unit_status, testing.BlockedStatus)


@pytest.mark.parametrize(
    "leader, relation_ids, failing_relation_id, expected_status, expected_published",
    [
        pytest.param(True, [1], None, testing.ActiveStatus(), 1, id="single-relation"),
        pytest.param(True, [1, 2], None, testing.ActiveStatus(), 2, id="every-relation"),
        pytest.param(False, [1], None, testing.ActiveStatus(), 0, id="non-leader"),
        pytest.param(
            True,
            [1, 2],
            2,
            testing.ActiveStatus("1/2 relation(s) published"),
            1,
            id="partial-publish",
        ),
    ],
)
def test_config_changed_publishes_to_relations(
    monkeypatch: pytest.MonkeyPatch,
    leader: bool,
    relation_ids: list[int],
    failing_relation_id: int | None,
    expected_status: testing.ActiveStatus,
    expected_published: int,
):
    """
    arrange: Create a charm context with ddos-protection relations and valid config.
    act: Run the config-changed event, optionally failing to save one relation.
    assert: The expected relations receive the configuration and the status is reported.
    """
    if failing_relation_id is not None:
        original_save = ops.Relation.save

        def _save(relation: ops.Relation, *args, **kwargs):
            if relation.id == failing_relation_id:
                raise ops.ModelError("relation is not available")
            return original_save(relation, *args, **kwargs)

        monkeypatch.setattr(ops.Relation, "save", _save)

    ctx = testing.Context(HAProxyDDoSProtectionConfiguratorCharm)
    relations = [
        testing.Relation(
            "ddos-protection",
            id=relation_id,
            interface="ddos_protection",
            remote_app_name=f"haproxy-{relation_id}",
        )
        for relation_id in relation_ids
    ]
    state = testing.State(
        leader=leader,
        relations=relations,
        config={
            "rate-limit-requests-per-minute": 100,
            "rate-limit-connections-per-minute": 50,
            "concurrent-connections-limit": 1000,
            "error-rate-per-minute": 10,
            "limit-policy-http": "reject",
            "limit-policy-tcp": "reject",
            "ip-allow-list": "192.168.1.1, 192.168.1.0/24",
            "http-request-timeout": 30,
            "http-keepalive-timeout": 60,
            "client-timeout": 50,
            "deny-paths": "/admin, /internal",
        },
    )

    out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == expected_status
    published_relations = [
        rel for rel in out.relations if rel.endpoint == "ddos-protection" and rel.local_app_data
    ]
    assert len(published_relations) == expected_published
    expected_app_data = {
        "rate_limit_requests_per_minute": 100,
        "rate_limit_connections_per_minute": 50,
        "concurrent_connections_limit": 1000,
        "error_rate": 10,
        "limit_policy_http": "reject",
        "limit_policy_tcp": "reject",
        "policy_status_code": None,
        "ip_allow_list": ["192.168.1.1", "192.168.1.0/24"],
        "http_request_timeout": 30,
        "http_keepalive_timeout": 60,
        "client_timeout": 50,
        "deny_paths": ["/admin", "/internal"],
    }
    for relation in published_relations:
        assert relation.local_app_data is not None
        assert {
            key: json.loads(value) for key, value in relation.local_app_data.items()
        } == expected_app_data
