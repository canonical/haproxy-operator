# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test settings for the haproxy_route_policy project."""

from .settings import *  # noqa: F401, F403

SECRET_KEY = "django-insecure-test-key-do-not-use-in-production"

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
