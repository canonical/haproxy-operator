# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database models for the haproxy-route-policy application."""

import typing
from django.db import models
from validators import domain
from django.core.exceptions import ValidationError

class RequestStatus(models.TextChoices):
    """Database values and human-readable labels for BackendRequest status.

    Each member's value is stored in the database; the label is the
    capitalised form produced automatically by Django TextChoices.
    """

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


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
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        db_index=True,
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
