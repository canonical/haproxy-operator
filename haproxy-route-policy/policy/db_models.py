# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database models for the haproxy-route-policy application."""

from datetime import datetime
import typing
from django.db import models
from validators import domain
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

REQUEST_STATUS_PENDING = "pending"
REQUEST_STATUS_ACCEPTED = "accepted"
REQUEST_STATUS_REJECTED = "rejected"

REQUEST_STATUSES = [
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_ACCEPTED,
    REQUEST_STATUS_REJECTED,
]

REQUEST_STATUS_CHOICES = [(status, status) for status in REQUEST_STATUSES]


def validate_hostname_acls(value: typing.Any):
    """Validate that the value is a list of valid hostnames."""
    logger.info("Validating hostname_acls: %s", value)
    if not isinstance(value, list):
        raise ValidationError("hostname_acls must be a list.")
    if invalid_hostnames := [
        hostname for hostname in typing.cast(list, value) if not domain(hostname)
    ]:
        raise ValidationError(f"Invalid hostnames: {', '.join(invalid_hostnames)}")


class BackendRequest(models.Model):
    """A backend request submitted via the haproxy-route relation.

    Attrs:
        id: Auto-incrementing primary key.
        relation_id: The Juju relation ID this request originated from.
        hostname_acls: Hostnames requested for routing.
        backend_name: The name of the backend in the HAProxy config.
        paths: URL paths requested for routing.
        port: The frontend port that should be opened by HAProxy.
        status: Current approval status (pending, accepted, rejected).
        created_at: Timestamp when the request was created.
        updated_at: Timestamp when the request was last updated.
    """

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    relation_id: models.IntegerField = models.IntegerField()
    hostname_acls: models.JSONField = models.JSONField(
        default=list, validators=[validate_hostname_acls], blank=True
    )
    backend_name: models.TextField = models.TextField()
    paths: models.JSONField = models.JSONField(default=list, blank=True)
    port: models.IntegerField = models.IntegerField()
    status: models.TextField = models.TextField(
        choices=REQUEST_STATUS_CHOICES,
        default=REQUEST_STATUS_PENDING,
        db_index=True,
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "id": self.id,
            "relation_id": self.relation_id,
            "hostname_acls": self.hostname_acls,
            "backend_name": self.backend_name,
            "paths": self.paths,
            "port": self.port,
            "status": self.status,
            "created_at": typing.cast(datetime, self.created_at).isoformat()
            if self.created_at
            else None,
            "updated_at": typing.cast(datetime, self.updated_at).isoformat()
            if self.updated_at
            else None,
        }

    @classmethod
    def required_fields(cls):
        """Return a list of fields required for creating a BackendRequest."""
        return ["relation_id", "backend_name", "port"]
