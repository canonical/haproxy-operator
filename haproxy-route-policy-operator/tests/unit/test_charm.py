# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route-policy-operator charm."""

from unittest.mock import patch

import pytest
from ops import testing

from charm import (
    DJANGO_ADMIN_CREDENTIALS_SECRET_LABEL,
    DJANGO_SECRET_KEY_SECRET_LABEL,
    HaproxyRoutePolicyCharm,
)


def _database_relation() -> testing.Relation:
    """Build a database relation carrying complete credentials."""
    return testing.Relation(
        "database",
        remote_app_data={
            "endpoints": "10.0.0.10:5432",
            "database": "haproxy_route_policy",
            "username": "policy",
            # Ignore bandit warning as this is for testing.
            "password": "secret",  # nosec
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

    with (
        patch("charm.install_snap") as install_snap_mock,
    ):
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
    state = testing.State(
        relations=[_database_relation()],
        secrets=[
            testing.Secret(
                label=DJANGO_SECRET_KEY_SECRET_LABEL, tracked_content={"secret-key": "test"}
            ),
            testing.Secret(
                label=DJANGO_ADMIN_CREDENTIALS_SECRET_LABEL,
                # Ignore bandit warning as this is for testing.
                tracked_content={"username": "admin", "password": "admin"},  # nosec
            ),
        ],
    )

    with (
        patch("charm.install_snap") as install_snap_mock,
        patch("charm.configure_snap") as configure_mock,
        patch("charm.run_migrations") as migrate_mock,
        patch("charm.start_gunicorn_service") as start_mock,
        patch("charm.create_or_update_user") as create_or_update_user_mock,
    ):
        out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    install_snap_mock.assert_called_once()
    configure_mock.assert_called_once()
    migrate_mock.assert_called_once()
    start_mock.assert_called_once()
    create_or_update_user_mock.assert_called_once()


@pytest.mark.parametrize(
    "secrets",
    [
        pytest.param(
            [
                testing.Secret(
                    label=DJANGO_SECRET_KEY_SECRET_LABEL, tracked_content={"secret-key": "test"}
                )
            ],
            id="missing-admin-credentials",
        ),
        pytest.param(
            [
                testing.Secret(
                    label=DJANGO_ADMIN_CREDENTIALS_SECRET_LABEL,
                    # Ignore bandit warning as this is for testing.
                    tracked_content={"username": "admin", "password": "admin"},  # nosec
                )
            ],
            id="missing-secret-key",
        ),
    ],
)
def test_config_changed_missing_secrets(secrets):
    """
    arrange: create charm context with valid database relation credentials.
    act: run config-changed event.
    assert: snap is configured, migrations run, and service is started.
    """
    ctx = testing.Context(HaproxyRoutePolicyCharm)
    state = testing.State(relations=[_database_relation()], secrets=secrets)

    with (
        patch("charm.install_snap"),
        patch("charm.configure_snap"),
        patch("charm.run_migrations"),
    ):
        out = ctx.run(ctx.on.config_changed(), state)

    assert out.unit_status == testing.WaitingStatus(
        "Waiting for leader to set shared configuration."
    )


def test_config_changed_leader_create_secrets():
    """
    arrange: create charm context with valid database relation credentials.
    act: run config-changed event.
    assert: snap is configured, migrations run, and service is started.
    """
    ctx = testing.Context(HaproxyRoutePolicyCharm)
    state = testing.State(relations=[_database_relation()], secrets=[], leader=True)

    with (
        patch("charm.install_snap"),
        patch("charm.configure_snap"),
        patch("charm.run_migrations"),
        patch("charm.start_gunicorn_service"),
        patch("charm.create_or_update_user"),
    ):
        out = ctx.run(ctx.on.config_changed(), state)

    assert len(list(out.secrets)) == 2
