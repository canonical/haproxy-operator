# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the haproxy-spoe-auth charm."""

import logging

import ops.testing

logger = logging.getLogger(__name__)


def test_install(context_with_mocks, base_state):
    """Test charm install event.

    arrange: prepare base state
    act: run install hook
    assert: service install is called
    """
    context, (install_mock, reconcile_mock) = context_with_mocks
    state = ops.testing.State(**base_state)
    context.run(context.on.install(), state)
    install_mock.assert_called_once()
    reconcile_mock.assert_called_once()


def test_config_changed(context_with_mocks, base_state):
    """Test charm config changed event.

    arrange: prepare base state
    act: trigger config changed hook
    assert: reconcile is called
    """
    context, (_, reconcile_mock) = context_with_mocks
    state = ops.testing.State(**base_state)
    context.run(context.on.config_changed(), state)
    reconcile_mock.assert_called_once()


def test_oauth_relation_changed(context_with_mocks, base_state):
    """Test oauth relation changed event.

    arrange: prepare state with oauth relation
    act: trigger relation changed hook
    assert: reconcile is called
    """
    context, (_, reconcile_mock) = context_with_mocks
    oauth_relation = ops.testing.Relation(
        endpoint="oauth",
        remote_app_name="oauth-provider",
        remote_app_data={
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "provider_url": "https://oauth.example.com",
        },
    )
    state = ops.testing.State(relations=[oauth_relation], **base_state)
    context.run(context.on.relation_changed(oauth_relation), state)
    reconcile_mock.assert_called_once()


def test_oauth_relation_broken(context_with_mocks, base_state):
    """Test oauth relation broken event.

    arrange: prepare state with oauth relation
    act: trigger relation broken hook
    assert: reconcile is called
    """
    context, (_, reconcile_mock) = context_with_mocks
    oauth_relation = ops.testing.Relation(
        endpoint="oauth",
        remote_app_name="oauth-provider",
        remote_app_data={
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "provider_url": "https://oauth.example.com",
        },
    )
    state = ops.testing.State(relations=[oauth_relation], **base_state)
    context.run(context.on.relation_broken(oauth_relation), state)
    reconcile_mock.assert_called_once()


def test_charm_state_without_oauth(context, base_state):
    """Test charm state when oauth is not configured.

    arrange: prepare base state without oauth
    act: get charm state
    assert: mode is NOAUTH
    """
    from state.charm_state import ProxyMode

    state = ops.testing.State(**base_state)
    with context.manager(context.on.config_changed(), state) as mgr:
        charm = mgr.charm
        charm_state = charm._get_charm_state()  # type: ignore[attr-defined]
        assert charm_state.mode == ProxyMode.NOAUTH
        assert charm_state.spoe_address == "127.0.0.1:3000"


def test_charm_state_with_oauth(context, base_state):
    """Test charm state when oauth is configured.

    arrange: prepare state with oauth relation
    act: get charm state
    assert: mode is OAUTH
    """
    from state.charm_state import ProxyMode

    oauth_relation = ops.testing.Relation(
        endpoint="oauth",
        remote_app_name="oauth-provider",
        remote_app_data={
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "provider_url": "https://oauth.example.com",
        },
    )
    state = ops.testing.State(relations=[oauth_relation], **base_state)
    with context.manager(context.on.config_changed(), state) as mgr:
        charm = mgr.charm
        charm_state = charm._get_charm_state()  # type: ignore[attr-defined]
        assert charm_state.mode == ProxyMode.OAUTH
