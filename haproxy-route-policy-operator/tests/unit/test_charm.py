# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route-policy-operator charm."""

from unittest.mock import patch

from ops import testing

from charm import HaproxyRoutePolicyCharm


def _database_relation() -> testing.Relation:
    """Build a database relation carrying complete credentials."""
    return testing.Relation(
        "database",
        remote_app_data={
            "endpoints": "10.0.0.10:5432",
            "database": "haproxy_route_policy",
            "username": "policy",
            "password": "secret",
        },
    )


def test_install_without_relation_sets_waiting_status():
    """
    arrange: create charm context without database relation.
    act: run install event.
    assert: snap install is invoked and unit waits for database relation data.
    """
    ctx = testing.Context(HaproxyRoutePolicyCharm)
    state = testing.State()

    with patch("charm.install_snap") as install_snap_mock:
        out = ctx.run(ctx.on.install(), state)

    install_snap_mock.assert_called_once_with()
    assert isinstance(out.unit_status, testing.BlockedStatus)


def test_config_changed_reconciles_snap_with_database_credentials():
    """
    arrange: create charm context with valid database relation credentials.
    act: run config-changed event.
    assert: snap is configured, migrations run, and service is started.
    """
    ctx = testing.Context(HaproxyRoutePolicyCharm)
    state = testing.State(relations=[_database_relation()])

    with (
        patch("charm.install_snap") as install_snap_mock,
        patch("charm.configure_snap") as configure_mock,
        patch("charm.run_migrations") as migrate_mock,
        patch("charm.start_gunicorn_service") as start_mock,
    ):
        out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    install_snap_mock.assert_called_once()
    configure_mock.assert_called_once()
    migrate_mock.assert_called_once()
    start_mock.assert_called_once()
