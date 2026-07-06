# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Middleware for handling database connection errors."""

import logging

from django.db import OperationalError, DatabaseError
from django.http import JsonResponse
from rest_framework.status import HTTP_500_INTERNAL_SERVER_ERROR

logger = logging.getLogger(__name__)


class BaseMiddleware:
    """Base middleware class to provide common structure for all middleware."""

    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response

    def __call__(self, request):
        """Process the request."""
        return self.get_response(request)


class DatabaseErrorMiddleware(BaseMiddleware):
    """Catch database connection errors and return a generic 503 response.

    This prevents the application's stack trace from being exposed to the client
    when the database is unreachable or encounters a connection-level error.
    """

    def process_exception(self, _request, exception):
        """Handle database errors raised during view processing."""
        if isinstance(exception, (OperationalError, DatabaseError)):
            logger.error("Database error: %s", exception)
            return JsonResponse(
                {"error": "A database error occurred. Please try again later."},
                status=HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return None
