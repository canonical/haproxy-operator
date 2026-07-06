# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django settings for running tests with SQLite in an authenticated setup."""

from haproxy_route_policy.settings import *  # noqa: F401, F403

# Mock secret key for testing.
SECRET_KEY = "test-secret-key"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
