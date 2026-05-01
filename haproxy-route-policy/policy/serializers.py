# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Serializers for the haproxy-route-policy application."""

from rest_framework import serializers
from policy.db_models import BackendRequest, Rule, RULE_KIND_HOSTNAME_AND_PATH_MATCH
import typing
from validators import domain


def is_valid_path(value: typing.Any):
    """Validate that the value is a list of valid URL paths."""
    return not isinstance(value, str) or not value.startswith("/")


class BackendRequestSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = BackendRequest
        fields = "__all__"


class RuleSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Rule
        fields = "__all__"

    def validate(self, attrs):
        """Custom validation logic for the Rule model."""
        if attrs.get("kind") == RULE_KIND_HOSTNAME_AND_PATH_MATCH:
            if not isinstance(attrs.get("parameters"), dict):
                raise serializers.ValidationError(
                    "The parameters field must be a JSON object."
                )

            if hostnames := typing.cast(dict, attrs.get("parameters")).get("hostnames"):
                if invalid_hostnames := [
                    hostname for hostname in hostnames if not domain(hostname)
                ]:
                    raise serializers.ValidationError(
                        f"Invalid hostname(s) in rule: {', '.join(invalid_hostnames)}"
                    )

            if paths := typing.cast(dict, attrs.get("parameters")).get("paths"):
                if invalid_paths := [path for path in paths if is_valid_path(path)]:
                    raise serializers.ValidationError(
                        f"Invalid path(s) in rule: {', '.join([str(path) for path in invalid_paths])}"
                    )
        if attrs.get("kind") == "backend_match":
            if not isinstance(attrs.get("parameters"), dict):
                raise serializers.ValidationError(
                    "The parameters field must be a JSON object."
                )
            if not attrs["parameters"].get("backend_name"):
                raise serializers.ValidationError(
                    "The parameters field must contain a 'backend_name' key for backend_match rules."
                )
        return attrs
