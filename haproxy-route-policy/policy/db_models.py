# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database models for the haproxy-route-policy application."""

import typing
import uuid
from django.db import models
from validators import domain
from django.core.exceptions import ValidationError

REQUEST_STATUS_PENDING = "pending"
REQUEST_STATUS_ACCEPTED = "accepted"
REQUEST_STATUS_REJECTED = "rejected"

# Note: changing these values will require a data migration to update the database schema.
REQUEST_STATUSES = [
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_ACCEPTED,
    REQUEST_STATUS_REJECTED,
]

REQUEST_STATUS_CHOICES = [(status, status) for status in REQUEST_STATUSES]

RULE_ACTION_ALLOW = "allow"
RULE_ACTION_DENY = "deny"

RULE_ACTIONS = [
    RULE_ACTION_ALLOW,
    RULE_ACTION_DENY,
]

RULE_ACTION_CHOICES = [(action, action) for action in RULE_ACTIONS]

RULE_KIND_HOSTNAME_AND_PATH_MATCH = "hostname_and_path_match"

RULE_KINDS = [
    RULE_KIND_HOSTNAME_AND_PATH_MATCH,
]

RULE_KIND_CHOICES = [(kind, kind) for kind in RULE_KINDS]


def validate_hostname_acls(value: typing.Any):
    """Validate that the value is a list of valid hostnames."""
    if not isinstance(value, list):
        raise ValidationError("hostname_acls must be a list.")
    if invalid_hostnames := [
        hostname for hostname in typing.cast(list, value) if not domain(hostname)
    ]:
        raise ValidationError(f"Invalid hostnames: {', '.join(invalid_hostnames)}")


def validate_port(value: typing.Any):
    """Validate that the value is a valid TCP port number."""
    if not isinstance(value, int) or not (1 <= value <= 65535):
        raise ValidationError("port must be an integer between 1 and 65535.")


def validate_paths(value: typing.Any):
    """Validate that the value is a list of valid URL paths."""
    if not isinstance(value, list):
        raise ValidationError("paths must be a list.")
    if invalid_paths := [
        path
        for path in typing.cast(list, value)
        if not isinstance(path, str) or not path.startswith("/")
    ]:
        raise ValidationError(
            f"Invalid paths: {', '.join(str(path) for path in invalid_paths)}"
        )


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
    backend_name: models.TextField = models.TextField(unique=True)
    paths: models.JSONField = models.JSONField(
        default=list, validators=[validate_paths], blank=True
    )
    port: models.IntegerField = models.IntegerField(validators=[validate_port])
    status: models.TextField = models.TextField(
        choices=REQUEST_STATUS_CHOICES,
        default=REQUEST_STATUS_PENDING,
        db_index=True,
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)


class Rule(models.Model):
    """A rule used to evaluate backend requests.

    Rules are matched against incoming backend requests to automatically
    accept or deny them. Rules have a priority and an action (allow/deny).

    Attrs:
        id: UUID primary key.
        kind: The type of rule (e.g. hostname_and_path_match, match_request_id).
        parameters: The rule parameters, structure depends on kind.
        action: Whether the rule allows or denies matching requests.
        priority: Rule priority (higher = evaluated first, deny wins on tie).
        comment: Optional human-readable comment.
        created_at: Timestamp when the rule was created.
        updated_at: Timestamp when the rule was last updated.
    """

    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    kind: models.TextField = models.TextField(choices=RULE_KIND_CHOICES)
    parameters: models.JSONField = models.JSONField()
    action: models.TextField = models.TextField(choices=RULE_ACTION_CHOICES)
    priority: models.IntegerField = models.IntegerField(default=0, blank=True)
    comment: models.TextField = models.TextField(default="", blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
