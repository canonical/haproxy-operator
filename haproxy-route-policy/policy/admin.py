# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

from django.contrib import admin
from .db_models import BackendRequest, Rule


@admin.register(BackendRequest)
class BackendRequestAdmin(admin.ModelAdmin):
    pass


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    pass
