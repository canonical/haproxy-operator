# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for managing the haproxy-route-policy snap."""

from __future__ import annotations

import subprocess  # nosec
from typing import Any

from charmlibs import snap

SNAP_NAME = "haproxy-route-policy"


def install_snap(channel: str = "latest/edge") -> None:
    """Install or refresh the route-policy snap."""
    cache = snap.SnapCache()
    package = cache[SNAP_NAME]
    package.ensure(snap.SnapState.Latest, channel=channel)


def configure_snap(config: dict[str, str | bool]) -> None:
    """Apply snap configuration if any value changed."""
    package = snap.SnapCache()[SNAP_NAME]
    existing = package.get(None, typed=True)
    to_set: dict[str, Any] = {}
    for key, value in config.items():
        if existing.get(key) != value:
            to_set[key] = value
    if to_set:
        package.set(to_set, typed=True)


def run_migrations() -> None:
    """Run first-time and subsequent database migrations."""
    subprocess.run(  # nosec
        [f"{SNAP_NAME}.manage", "migrate", "--noinput"],
        check=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def start_gunicorn_service() -> None:
    """Ensure the snap gunicorn app is running."""
    package = snap.SnapCache()[SNAP_NAME]
    package.start()
