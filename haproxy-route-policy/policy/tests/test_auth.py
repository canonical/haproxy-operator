# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Authentication tests."""

from django.test import TestCase, tag
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@tag("auth")
class TestAuthenticationRequired(TestCase):
    """Tests that endpoints require authentication."""

    def setUp(self):
        self.client = APIClient()

    def test_list_requests_unauthenticated(self):
        """GET /api/v1/requests returns 401/403 without auth."""
        response = self.client.get("/api/v1/requests")
        self.assertIn(response.status_code, [401, 403])

    def test_create_requests_unauthenticated(self):
        """POST /api/v1/requests returns 401/403 without auth."""
        response = self.client.post("/api/v1/requests", [], format="json")
        self.assertIn(response.status_code, [401, 403])

    def test_list_rules_unauthenticated(self):
        """GET /api/v1/rules returns 401/403 without auth."""
        response = self.client.get("/api/v1/rules")
        self.assertIn(response.status_code, [401, 403])


@tag("auth")
class TestAuthenticated(TestCase):
    """Tests endpoints as an authenticated user."""

    def setUp(self):
        self.user = User.objects.create_user("admin", "admin@example.com", "admin")
        self.client = APIClient()
        # Add nosec to ignore bandit warning as this is for testing.
        self.client.login(username="admin", password="admin")  # nosec

    def test_create_requests_authenticated(self):
        """POST /api/v1/requests returns 201 with auth."""
        payload = [
            {
                "relation_id": 1,
                "hostname_acls": ["example.com"],
                "backend_name": "backend-1",
                "paths": ["/api"],
                "port": 443,
            },
            {
                "relation_id": 2,
                "backend_name": "backend-2",
                "port": 443,
            },
        ]
        response = self.client.post("/api/v1/requests", data=payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_create_rules_authenticated(self):
        """POST /api/v1/rules returns 201 with auth."""
        payload = {
            "name": "Test Rule",
            "action": "allow",
            "kind": "hostname_and_path_match",
            "parameters": {
                "hostnames": ["example.com"],
                "paths": ["/api"],
            },
        }
        response = self.client.post("/api/v1/rules", data=payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_list_requests_authenticated(self):
        """GET /api/v1/requests returns 200 with auth."""
        response = self.client.get("/api/v1/requests")
        self.assertEqual(response.status_code, 200)

    def test_list_rules_authenticated(self):
        """GET /api/v1/rules returns 200 with auth."""
        response = self.client.get("/api/v1/rules")
        self.assertEqual(response.status_code, 200)
