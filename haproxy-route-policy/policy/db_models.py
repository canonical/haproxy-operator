# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database models for the haproxy-route-policy application."""

import typing
from django.db import models
from validators import domain
from django.core.exceptions import ValidationError
import uuid

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
    if not isinstance(value, list):
        raise ValidationError("hostname_acls must be a list.")
    if invalid_hostnames := [
        hostname for hostname in typing.cast(list, value) if not domain(hostname)
    ]:
        raise ValidationError(f"Invalid hostnames: {', '.join(invalid_hostnames)}")


class BackendRequest(models.Model):
    """A backend request submitted via the haproxy-route relation.

    Attrs:
        id: Request UUID.
        relation_id: The Juju relation ID this request originated from.
        hostname_acls: Hostnames requested for routing.
        backend_name: The name of the backend in the HAProxy config.
        paths: URL paths requested for routing.
        port: The frontend port that should be opened by HAProxy.
        status: Current approval status (pending, accepted, rejected).
        created_at: Timestamp when the request was created.
        updated_at: Timestamp when the request was last updated.
    """

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
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
