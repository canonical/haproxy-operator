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


def test_charm_state_without_oauth(context_with_mocks, base_state):
    """Test charm status when oauth is not configured.

    arrange: prepare base state without oauth
    act: trigger config changed
    assert: charm is active without authentication
    """
    context, (_, reconcile_mock) = context_with_mocks
    state = ops.testing.State(**base_state)
    out = context.run(context.on.config_changed(), state)
    reconcile_mock.assert_called_once()
    assert out.unit_status == ops.testing.ActiveStatus("Service running without authentication")


def test_charm_state_with_oauth(context_with_mocks, base_state):
    """Test charm status when oauth is configured.

    arrange: prepare state with oauth relation
    act: trigger config changed
    assert: charm is active with oauth
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
    out = context.run(context.on.config_changed(), state)
    reconcile_mock.assert_called_once()
    assert out.unit_status == ops.testing.ActiveStatus("OAuth authentication enabled")
