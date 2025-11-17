# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for SPOE authentication state."""

from unittest.mock import MagicMock

from state.spoe_auth import SpoeAuthInformation


def test_spoe_auth_information_no_relation():
    """Test SpoeAuthInformation when no relation exists."""
    charm = MagicMock()
    charm.model.get_relation.return_value = None

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert len(spoe_info.agents) == 0


def test_spoe_auth_information_with_relation_no_app():
    """Test SpoeAuthInformation when relation exists but has no app data."""
    charm = MagicMock()
    relation = MagicMock()
    relation.app = None
    relation.units = []
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert len(spoe_info.agents) == 0


def test_spoe_auth_information_with_valid_data():
    """Test SpoeAuthInformation when relation has valid data."""
    charm = MagicMock()
    relation = MagicMock()
    app = MagicMock()
    unit = MagicMock()
    unit.name = "spoe-auth/0"
    relation.app = app
    relation.units = [unit]
    relation.data = {
        app: {
            "oidc-callback-path": "/oauth2/callback",
            "oidc-callback-hostname": "example.com",
            "var-authenticated": "sess.auth.authenticated",
            "var-redirect-url": "sess.auth.redirect_url",
            "spoe-config-path": "/etc/haproxy/spoe_auth.conf",
        },
        unit: {
            "agent-address": "10.0.0.1",
            "spop-port": "9000",
            "oidc-callback-port": "8080",
        },
    }
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is True
    assert len(spoe_info.agents) == 1
    assert spoe_info.agents[0].address == "10.0.0.1"
    assert spoe_info.agents[0].spop_port == 9000
    assert spoe_info.agents[0].oidc_callback_port == 8080
    assert spoe_info.oidc_callback_path == "/oauth2/callback"
    assert spoe_info.oidc_callback_hostname == "example.com"


def test_spoe_auth_information_with_invalid_port():
    """Test SpoeAuthInformation when port is invalid."""
    charm = MagicMock()
    relation = MagicMock()
    app = MagicMock()
    unit = MagicMock()
    unit.name = "spoe-auth/0"
    relation.app = app
    relation.units = [unit]
    relation.data = {
        app: {
            "oidc-callback-path": "/oauth2/callback",
            "oidc-callback-hostname": "example.com",
            "var-authenticated": "sess.auth.authenticated",
            "var-redirect-url": "sess.auth.redirect_url",
            "spoe-config-path": "/etc/haproxy/spoe_auth.conf",
        },
        unit: {
            "agent-address": "10.0.0.1",
            "spop-port": "invalid",
            "oidc-callback-port": "8080",
        },
    }
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert len(spoe_info.agents) == 0


def test_spoe_auth_information_with_partial_data():
    """Test SpoeAuthInformation when only address is provided."""
    charm = MagicMock()
    relation = MagicMock()
    app = MagicMock()
    unit = MagicMock()
    unit.name = "spoe-auth/0"
    relation.app = app
    relation.units = [unit]
    relation.data = {
        app: {
            "oidc-callback-path": "/oauth2/callback",
            "oidc-callback-hostname": "example.com",
            "var-authenticated": "sess.auth.authenticated",
            "var-redirect-url": "sess.auth.redirect_url",
            "spoe-config-path": "/etc/haproxy/spoe_auth.conf",
        },
        unit: {"agent-address": "10.0.0.1"},
    }
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert len(spoe_info.agents) == 0


def test_spoe_auth_information_missing_app_config():
    """Test SpoeAuthInformation when app config is incomplete."""
    charm = MagicMock()
    relation = MagicMock()
    app = MagicMock()
    unit = MagicMock()
    unit.name = "spoe-auth/0"
    relation.app = app
    relation.units = [unit]
    relation.data = {
        app: {
            "oidc-callback-path": "/oauth2/callback",
            # Missing other required fields
        },
        unit: {
            "agent-address": "10.0.0.1",
            "spop-port": "9000",
            "oidc-callback-port": "8080",
        },
    }
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
