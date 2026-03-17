# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""REST API views for backend requests."""

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest, JsonResponse
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from .db_models import BackendRequest, REQUEST_STATUS_PENDING


class ListCreateRequestsView(APIView):
    """View for listing and bulk-creating backend requests."""

    def get(self, request):
        """List all requests, optionally filtered by status."""
        status = request.GET.get("status")
        queryset = BackendRequest.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        return JsonResponse([r.to_dict() for r in queryset.order_by("id")], safe=False)

    def post(self, request):
        """Bulk create backend requests.

        All new requests are set to 'pending' (evaluation logic is deferred).
        """
        if not isinstance(request.data, list):
            return JsonResponse(
                {"error": "Expected a list of request objects."}, status=400
            )

        created = []
        try:
            for item in request.data:
                backend_request = BackendRequest.objects.create(
                    relation_id=item.get("relation_id"),
                    hostname_acls=item.get("hostname_acls", []),
                    backend_name=item.get("backend_name"),
                    paths=item.get("paths", []),
                    port=item.get("port"),
                    status=REQUEST_STATUS_PENDING,
                )
                created.append(backend_request.to_dict())
        except ValidationError as e:
            return HttpResponseBadRequest({"error": str(e)}, status=400)
        return JsonResponse(created, safe=False, status=201)


class RequestDetailView(APIView):
    """View for getting or deleting a single backend request."""

    def get(self, request, pk):
        """Get a request by ID."""
        try:
            backend_request = BackendRequest.objects.get(pk=pk)
        except BackendRequest.DoesNotExist:
            return HttpResponseNotFound()
        return JsonResponse(backend_request.to_dict())

    def delete(self, request, pk):
        """Delete a request by ID."""
        BackendRequest.objects.filter(pk=pk).delete()
        return HttpResponse(status=204)
