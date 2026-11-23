# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django settings for running tests with SQLite."""

from haproxy_route_policy.settings import *  # noqa: F401, F403

# Mock secret key for testing.
SECRET_KEY = "test-secret-key"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# The tests run without `collectstatic`, so STATIC_ROOT does not exist and
# WhiteNoise would warn "No directory at ..." when its middleware starts. The
# unit tox envs promote warnings to errors, so serve static files on demand
# instead of from a pre-collected directory.
WHITENOISE_AUTOREFRESH = True
