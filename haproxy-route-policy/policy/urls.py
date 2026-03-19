# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""URL configuration for the policy app."""

from django.urls import path

from policy import views

urlpatterns = [
    path(
        "api/v1/requests",
        views.ListCreateRequestsView.as_view(),
        name="api-requests",
    ),
    path(
        "api/v1/requests/<str:pk>",
        views.RequestDetailView.as_view(),
        name="api-request-detail",
    ),
]
