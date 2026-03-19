from rest_framework import serializers
from policy.db_models import (
    BackendRequest,
)


class BackendRequestSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = BackendRequest
        fields = "__all__"
