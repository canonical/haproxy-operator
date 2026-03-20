# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Serializers for the haproxy-route-policy application."""

from rest_framework import serializers
from policy.db_models import (
    BackendRequest,
)


class BackendRequestSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = BackendRequest
        fields = "__all__"
