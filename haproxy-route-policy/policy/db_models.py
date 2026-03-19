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


def is_valid_path(value: typing.Any):
    """Validate that the value is a list of valid URL paths."""
    return not isinstance(value, str) or not value.startswith("/")


class Rule(models.Model):
    """A rule used to evaluate backend requests.

    Rules are matched against incoming backend requests to automatically
    accept or deny them. Rules have a priority and an action (allow/deny).

    Attrs:
        id: UUID primary key.
        kind: The type of rule (e.g. hostname_and_path_match, match_request_id).
        value: The rule value, structure depends on kind.
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
    value: models.JSONField = models.JSONField()
    action: models.TextField = models.TextField(choices=RULE_ACTION_CHOICES)
    priority: models.IntegerField = models.IntegerField(default=0, blank=True)
    comment: models.TextField = models.TextField(default="", blank=True)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        """Custom validation logic for the Rule model."""
        if self.kind == RULE_KIND_HOSTNAME_AND_PATH_MATCH:
            if not isinstance(self.value, dict):
                raise ValidationError("The value field must be a JSON object.")

            if hostnames := self.value.get("hostnames"):
                if invalid_hostnames := [
                    hostname for hostname in hostnames if not domain(hostname)
                ]:
                    raise ValidationError(
                        f"Invalid hostname(s) in rule: {', '.join(invalid_hostnames)}"
                    )

            if paths := self.value.get("paths"):
                if invalid_paths := [path for path in paths if is_valid_path(path)]:
                    raise ValidationError(
                        f"Invalid path(s) in rule: {', '.join([str(path) for path in invalid_paths])}"
                    )
