# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""REST API views for backend requests."""

import uuid
from typing import Any
from venv import logger
from policy.db_models import BackendRequest
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_204_NO_CONTENT,
)
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db import transaction
from policy import serializers
from .db_models import REQUEST_STATUSES


class ListCreateRequestsView(APIView):
    """View for listing and bulk-creating backend requests."""

    def get(self, request):
        """List all requests, optionally filtered by status."""
        status = request.GET.get("status")
        if status and status not in REQUEST_STATUSES:
            return Response(
                {"error": "Invalid status filter."}, status=HTTP_400_BAD_REQUEST
            )
        filters = {"status": status} if status else {}
        queryset = BackendRequest.objects.all().filter(**filters)
        serializer = serializers.BackendRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Bulk create backend requests.

        All new requests are set to 'pending' (evaluation logic is deferred).
        """
        if not isinstance(request.data, list):
            return Response(
                {"error": "Expected a list of request objects."},
                status=HTTP_400_BAD_REQUEST,
            )

        created = []
        try:
            with transaction.atomic():
                for backend_request in request.data:
                    serializer = serializers.BackendRequestSerializer(
                        data=backend_request
                    )
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        created.append(serializer.data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response(
                {"error": "Invalid request data."}, status=HTTP_400_BAD_REQUEST
            )
        return Response(created, status=HTTP_201_CREATED)


class RequestDetailView(APIView):
    """View for getting or deleting a single backend request."""

    def get(self, _request, pk):
        """Get a request by ID."""
        try:
            backend_request = BackendRequest.objects.get(pk=uuid_primary_key(pk))
            serializer = serializers.BackendRequestSerializer(backend_request)
        except BackendRequest.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        except (ValueError, AttributeError):
            return Response(
                {"error": "Invalid request ID."}, status=HTTP_400_BAD_REQUEST
            )
        return Response(serializer.data)

    def delete(self, _request, pk):
        """Delete a request by ID."""
        try:
            BackendRequest.objects.filter(pk=uuid_primary_key(pk)).delete()
        except (AttributeError, ValueError):
            logger.warning(f"Attempted to delete request with invalid UUID: {pk}")
        return Response(status=HTTP_204_NO_CONTENT)


def uuid_primary_key(pk: Any) -> str:
    """Validate that the passed request parameter is a valid UUID string.

    The calling methods are responsible for catching ValueError and AttributeError.
    """
    return str(uuid.UUID(str(pk), version=4))
