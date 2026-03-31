# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route-policy-operator charm."""

from unittest.mock import patch

from ops import testing

from charm import HaproxyRoutePolicyCharm


def _postgresql_relation() -> testing.Relation:
    """Build a postgresql relation carrying complete credentials."""
    return testing.Relation(
        "postgresql",
        remote_app_data={
            "endpoints": "10.0.0.10:5432",
            "database": "haproxy_route_policy",
            "username": "policy",
            "password": "secret",
        },
    )


def test_install_without_relation_sets_waiting_status():
    """
    arrange: create charm context without postgresql relation.
    act: run install event.
    assert: snap install is invoked and unit waits for postgresql relation data.
    """
    ctx = testing.Context(HaproxyRoutePolicyCharm)
    state = testing.State()

    with patch("charm.snap.install_snap") as install_snap_mock:
        out = ctx.run(ctx.on.install(), state)

    install_snap_mock.assert_called_once_with()
    assert isinstance(out.unit_status, testing.WaitingStatus)


def test_config_changed_reconciles_snap_with_postgresql_credentials():
    """
    arrange: create charm context with valid postgresql relation credentials.
    act: run config-changed event.
    assert: snap is configured, migrations run, and service is started.
    """
    ctx = testing.Context(HaproxyRoutePolicyCharm)
    state = testing.State(relations=[_postgresql_relation()])

    with (
        patch("charm.snap.configure_snap") as configure_mock,
        patch("charm.snap.run_migrations") as migrate_mock,
        patch("charm.snap.start_gunicorn_service") as start_mock,
    ):
        out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    configure_mock.assert_called_once()
    migrate_mock.assert_called_once()
    start_mock.assert_called_once()
