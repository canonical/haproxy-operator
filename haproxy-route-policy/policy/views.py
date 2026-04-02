# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""REST API views for backend requests and rules."""

from policy.db_models import BackendRequest, Rule
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_204_NO_CONTENT,
)
from django.http import Http404
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db import transaction
from policy import serializers
from .db_models import REQUEST_STATUSES
from policy.rule_engine import evaluate_request
from .serializers import BackendRequestSerializer, RuleSerializer


class ListCreateRequestsView(APIView):
    """View for listing and bulk-creating backend requests."""

    def get_request_by_backend_name(self, backend_name: str) -> BackendRequest | None:
        """Get a backend request by its backend name."""
        try:
            return BackendRequest.objects.get(backend_name=backend_name)
        except BackendRequest.DoesNotExist:
            return None

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

        Each new request is evaluated against existing rules immediately.
        If a matching rule is found, the request status is set accordingly.
        If no rules match, the request stays as 'pending'.
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
                    # Get the request with the same backend_name if it exists and update it, otherwise create a new one
                    req = self.get_request_by_backend_name(
                        backend_request.get("backend_name")
                    )
                    serializer = BackendRequestSerializer(req, data=backend_request)
                    if serializer.is_valid(raise_exception=True):
                        instance = BackendRequest(**serializer.validated_data)
                        # Evaluate rules and update status
                        instance.status = evaluate_request(instance)
                        instance.save()
                        created.append(BackendRequestSerializer(instance).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response(
                {"error": f"Invalid request data: {str(e)}"},
                status=HTTP_400_BAD_REQUEST,
            )
        return Response(created, status=HTTP_201_CREATED)


class RequestDetailView(APIView):
    """View for getting or deleting a single backend request."""

    def get(self, _request, pk):
        """Get a request by ID."""
        backend_request = get_object(BackendRequest, pk)
        serializer = serializers.BackendRequestSerializer(backend_request)
        return Response(serializer.data)

    def delete(self, _request, pk):
        """Delete a request by ID."""
        BackendRequest.objects.filter(pk=pk).delete()
        return Response(status=HTTP_204_NO_CONTENT)


class ListCreateRulesView(APIView):
    """View for listing and creating rules."""

    def get(self, request):
        """List all rules."""
        queryset = Rule.objects.all().order_by("-priority", "created_at")
        serializer = RuleSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new rule."""
        serializer = RuleSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=HTTP_201_CREATED)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class RuleDetailView(APIView):
    """View for getting, updating, or deleting a single rule."""

    def get(self, request, pk):
        """Get a rule by ID."""
        rule = get_object(Rule, pk)
        serializer = serializers.RuleSerializer(rule)
        return Response(data=serializer.data)

    def put(self, request, pk):
        """Update a rule by ID."""
        rule = get_object(Rule, pk)
        serializer = serializers.RuleSerializer(rule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete a rule by ID."""
        Rule.objects.filter(pk=pk).delete()
        return Response(status=HTTP_204_NO_CONTENT)
