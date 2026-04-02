# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Serializers for the haproxy-route-policy application."""

from rest_framework import serializers
from policy.db_models import (
    BackendRequest,
    Rule,
)


class BackendRequestSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = BackendRequest
        fields = "__all__"


class RuleSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = Rule
        fields = "__all__"
