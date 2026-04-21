# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from .db_models import BackendRequest, Rule
from .views import RequestRefreshView


@admin.register(BackendRequest)
class BackendRequestAdmin(admin.ModelAdmin):
    change_list_template = "policy/refresh_requests_form.html"
    readonly_fields = ("status",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "refresh/",
                self.admin_site.admin_view(self.refresh_requests),
                name="policy_backendrequest_refresh",
            ),
        ]
        return custom_urls + urls

    def refresh_requests(self, request):
        """Re-evaluate all backend requests by delegating to RequestRefreshView."""
        view = RequestRefreshView()
        view.get(request)
        count = BackendRequest.objects.count()
        self.message_user(
            request,
            f"Successfully refreshed {count} request(s).",
            messages.SUCCESS,
        )
        return HttpResponseRedirect(reverse("admin:policy_backendrequest_changelist"))


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    pass
