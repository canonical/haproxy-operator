# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Policy app configuration."""

from django.apps import AppConfig


class PolicyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "policy"
