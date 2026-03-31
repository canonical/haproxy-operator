# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for managing the haproxy-route-policy snap."""

from __future__ import annotations

import logging
import subprocess  # nosec
from typing import Any

from charmlibs import snap

SNAP_NAME = "haproxy-route-policy"
logger = logging.getLogger(__name__)


class HaproxyRoutePolicyDatabaseMigrationError(Exception):
    """Raised when database migrations fail."""


def install_snap(channel: str = "latest/edge") -> None:
    """Install or refresh the route-policy snap."""
    cache = snap.SnapCache()
    package = cache[SNAP_NAME]
    package.ensure(snap.SnapState.Latest, channel=channel)


def configure_snap(config: dict[str, Any]) -> None:
    """Apply snap configuration if any value changed."""
    package = snap.SnapCache()[SNAP_NAME]
    package.set(config, typed=True)


def run_migrations() -> None:
    """Run first-time and subsequent database migrations."""
    try:
        subprocess.run(  # nosec
            [f"{SNAP_NAME}.manage", "migrate", "--noinput"],
            check=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running migrations: {e.output}")
        raise HaproxyRoutePolicyDatabaseMigrationError("Database migrations failed") from e


def start_gunicorn_service() -> None:
    """Ensure the snap gunicorn app is running."""
    package = snap.SnapCache()[SNAP_NAME]
    package.start()


def create_or_update_user(username: str, password: str) -> None:
    """Create or update the HTTP proxy policy superuser.

    Args:
        username: The username.
        password: The password.

    Raises:
        RuntimeError: If the action failed.
    """
    try:
        subprocess.run(  # nosec
            [f"{SNAP_NAME}.manage", "upsertsuperuser"],
            env={
                "DJANGO_SUPERUSER_PASSWORD": password,
                "DJANGO_SUPERUSER_USERNAME": username,
            },
            check=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"failed to create/update Django user: {e.stdout}") from e
