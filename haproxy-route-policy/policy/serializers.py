from rest_framework import serializers
from policy.db_models import (
    BackendRequest,
)


class BackendRequestSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = BackendRequest
        fields = [
            "id",
            "relation_id",
            "hostname_acls",
            "backend_name",
            "paths",
            "port",
            "status",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Create and return a new `BackendRequest` instance, given the validated data.
        """
        return BackendRequest.objects.create(**validated_data)
