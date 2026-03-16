# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""REST API views for the policy application."""

import json

from django.db import transaction
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    JsonResponse,
)
from rest_framework import permissions
from rest_framework.views import APIView

import policy.models as models


class ListCreateRequestsView(APIView):
    """View for listing and bulk creating proxy requests."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """List all requests, with an optional status query parameter."""
        status = request.GET.get("status")
        if status:
            proxy_requests = models.Request.objects.filter(status=status)
        else:
            proxy_requests = models.Request.objects.all()
        return JsonResponse([r.to_jsonable() for r in proxy_requests], safe=False)

    def post(self, request):
        """Bulk create and evaluate requests.

        New requests are set to "pending" (evaluation logic skipped for now).
        """
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("invalid JSON")

        if not isinstance(data, list):
            return HttpResponseBadRequest(f"not a list: {data}")

        new_requests = {}

        for proxy_request in data:
            if not isinstance(proxy_request, dict):
                return HttpResponseBadRequest(f"not a json object: {proxy_request}")

            requirer = proxy_request.get("requirer")
            if requirer is None:
                return HttpResponseBadRequest(
                    f"missing requirer field: {proxy_request}"
                )

            try:
                validated_request = models.RequestInput(**proxy_request)
            except ValueError as e:
                return HttpResponseBadRequest(str(e))

            if validated_request.requirer in new_requests:
                return HttpResponseBadRequest(
                    f"duplicate requirer: {validated_request.requirer}"
                )

            new_requests[validated_request.requirer] = models.Request(
                requirer=validated_request.requirer,
                domains=validated_request.domains,
                auth=validated_request.auth,
                src_ips=list(validated_request.src_ips),
                implicit_src_ips=validated_request.implicit_src_ips,
                status=models.PROXY_STATUS_PENDING,
                accepted_auth=None,
            )

        with transaction.atomic():
            for model_request in new_requests.values():
                model_request.save()
            models.Request.objects.exclude(requirer__in=new_requests.keys()).delete()

        return JsonResponse(
            [r.to_jsonable() for r in new_requests.values()], safe=False
        )


class GetDeleteRequestView(APIView):
    """View for getting or deleting a single proxy request by ID."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Get a request by ID."""
        try:
            proxy_request = models.Request.objects.get(pk=pk)
        except models.Request.DoesNotExist:
            return HttpResponseNotFound()
        return JsonResponse(proxy_request.to_jsonable())

    def delete(self, request, pk):
        """Delete a request by ID."""
        try:
            models.Request.objects.get(pk=pk)
        except models.Request.DoesNotExist:
            return HttpResponseNotFound()
        models.Request.objects.filter(pk=pk).delete()
        return HttpResponse()
