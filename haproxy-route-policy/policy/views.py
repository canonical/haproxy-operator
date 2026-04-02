# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""REST API views for backend requests and rules."""

from policy.db_models import BackendRequest, Rule
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


class ListCreateRequestsView(APIView):
    """View for listing and bulk-creating backend requests."""

    def get(self, request):
        """List all requests, optionally filtered by status."""
        filter = (
            {"status": request.GET.get("status")} if request.GET.get("status") else {}
        )
        queryset = BackendRequest.objects.all().filter(**filter)
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
            backend_request = BackendRequest.objects.get(pk=pk)
            serializer = serializers.BackendRequestSerializer(backend_request)
        except BackendRequest.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        return Response(serializer.data)

    def delete(self, request, pk):
        """Delete a request by ID."""
        BackendRequest.objects.filter(pk=pk).delete()
        return Response(status=HTTP_204_NO_CONTENT)


class ListCreateRulesView(APIView):
    """View for listing and creating rules."""

    def get(self, request):
        """List all rules."""
        queryset = Rule.objects.all().order_by("-priority", "created_at")
        serializer = serializers.RuleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new rule."""
        data = request.data
        if not isinstance(data, dict):
            return Response(
                {"error": "Expected a JSON object."}, status=HTTP_400_BAD_REQUEST
            )

        try:
            serializer = serializers.RuleSerializer(data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        except IntegrityError:
            return Response(
                {"error": "Invalid rule data."}, status=HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data, status=HTTP_201_CREATED)


class RuleDetailView(APIView):
    """View for getting, updating, or deleting a single rule."""

    def get(self, request, pk):
        """Get a rule by ID."""
        try:
            rule = Rule.objects.get(pk=pk)
        except (Rule.DoesNotExist, ValueError):
            return Response(status=HTTP_404_NOT_FOUND)
        return Response(rule.to_dict())

    def put(self, request, pk):
        """Update a rule by ID."""
        try:
            rule = Rule.objects.get(pk=pk)
            serializer = serializers.RuleSerializer(rule)
        except (Rule.DoesNotExist, ValueError):
            return Response(status=HTTP_404_NOT_FOUND)

        data = request.data
        if not isinstance(data, dict):
            return Response(
                {"error": "Expected a JSON object."}, status=HTTP_400_BAD_REQUEST
            )
        # Update fields if provided
        if "kind" in data:
            rule.kind = data["kind"]
        if "value" in data:
            rule.value = data["value"]
        if "action" in data:
            rule.action = data["action"]
        if "priority" in data:
            rule.priority = data["priority"]
        if "comment" in data:
            rule.comment = data["comment"]

        try:
            rule.full_clean()
            rule.save()
        except ValidationError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response(serializer.data)

    def delete(self, request, pk):
        """Delete a rule by ID."""
        Rule.objects.filter(pk=pk).delete()
        return Response(status=HTTP_204_NO_CONTENT)
