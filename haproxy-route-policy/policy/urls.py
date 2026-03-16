# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""URL routing for the policy application."""

from django.urls import path

import policy.views as views

urlpatterns = [
    path(
        "api/v1/requests/<uuid:pk>",
        views.GetDeleteRequestView.as_view(),
        name="api-get-delete-request",
    ),
    path(
        "api/v1/requests",
        views.ListCreateRequestsView.as_view(),
        name="api-list-create-requests",
    ),
]
