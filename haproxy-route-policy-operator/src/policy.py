# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for managing the haproxy-route-policy snap."""

import logging
import os
import subprocess  # nosec
from typing import Any

import requests as http_requests
from charmlibs import snap
from charms.haproxy_route_policy.v0.haproxy_route_policy import (
    HaproxyRoutePolicyBackendRequest,
)
from pydantic import Field
from pydantic.dataclasses import dataclass

SNAP_NAME = "haproxy-route-policy"
DEFAULT_ENDPOINT = "http://localhost:8080"
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


def is_service_active() -> bool:
    """Check if the snap gunicorn app is active."""
    package = snap.SnapCache()[SNAP_NAME]
    return package.services["gunicorn"].get("active", False)


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
                **os.environ,
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


@dataclass
class EvaluatedBackendRequest(HaproxyRoutePolicyBackendRequest):
    """A backend request returned by the policy service with its evaluation status.

    Attributes:
        status: Evaluation status (pending, accepted, rejected).
    """

    status: str = Field(description="Evaluation status (pending, accepted, rejected)")


class HaproxyRoutePolicyAPIError(Exception):
    """Raised when the haproxy-route-policy API returns an error.

    Attributes:
        status_code: HTTP status code.
        message: Error message from the API.
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"API error {status_code}: {message}")


class HaproxyRoutePolicyClient:
    """Client for the haproxy-route-policy Django REST API.

    Communicates with the policy service exposed by the haproxy-route-policy
    snap to create, evaluate and manage backend requests.
    """

    def __init__(
        self,
        username: str,
        password: str,
        endpoint: str = DEFAULT_ENDPOINT,
    ) -> None:
        """Initialize the client.

        Args:
            username: Django admin username for basic auth.
            password: Django admin password for basic auth.
            endpoint: Base URL of the policy service.
        """
        self._endpoint = endpoint.rstrip("/")
        self._auth = (username, password)

    def refresh(
        self,
        backend_requests: list[HaproxyRoutePolicyBackendRequest],
    ) -> list[EvaluatedBackendRequest]:
        """Submit backend requests to the policy service for evaluation.

        Existing requests with the same ``backend_name`` are updated;
        new ones are created.  The policy service evaluates every request
        against its rule set and returns the current status.

        Args:
            backend_requests: list of backend requests from the requirer.

        Returns:
            List of evaluated backend requests with their status.
        """
        payload = [
            {
                "relation_id": req.relation_id,
                "backend_name": req.backend_name,
                "hostname_acls": list(req.hostname_acls),
                "paths": list(req.paths),
                "port": req.port,
            }
            for req in backend_requests
        ]
        response = http_requests.post(
            f"{self._endpoint}/api/v1/requests",
            json=payload,
            auth=self._auth,
            timeout=10,
        )
        self._raise_for_error(response)
        return [EvaluatedBackendRequest(**item) for item in response.json()]

    def list_requests(self, status: str | None = None) -> list[EvaluatedBackendRequest]:
        """List backend requests, optionally filtered by status.

        Args:
            status: Optional status filter (pending, accepted, rejected).

        Returns:
            List of evaluated backend requests.
        """
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        response = http_requests.get(
            f"{self._endpoint}/api/v1/requests",
            params=params,
            auth=self._auth,
            timeout=10,
        )
        self._raise_for_error(response)
        return [EvaluatedBackendRequest(**item) for item in response.json()]

    def _raise_for_error(self, response: http_requests.Response) -> None:
        """Raise :class:`HaproxyRoutePolicyAPIError` on non-2xx responses.

        Args:
            response: The HTTP response to check.

        Raises:
            HaproxyRoutePolicyAPIError: If the response status is not 2xx.
        """
        try:
            response.raise_for_status()
        except http_requests.exceptions.HTTPError as exc:
            raise HaproxyRoutePolicyAPIError(
                status_code=response.status_code, message=response.text
            ) from exc
