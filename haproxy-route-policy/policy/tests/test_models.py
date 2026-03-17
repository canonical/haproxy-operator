# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the BackendRequest model."""

from django.test import TestCase

from policy import db_models


class TestBackendRequestModel(TestCase):
    """Tests for BackendRequest model creation and serialisation."""

    def test_create_with_defaults(self):
        """Test creating a request with minimal required fields."""
        request = db_models.BackendRequest.objects.create(
            relation_id=1,
            backend_name="my-backend",
        )
        self.assertEqual(request.relation_id, 1)
        self.assertEqual(request.backend_name, "my-backend")
        self.assertEqual(request.hostname_acls, [])
        self.assertEqual(request.paths, [])
        self.assertIsNone(request.port)
        self.assertEqual(request.status, db_models.REQUEST_STATUS_PENDING)
        self.assertIsNotNone(request.created_at)
        self.assertIsNotNone(request.updated_at)

    def test_create_with_all_fields(self):
        """Test creating a request with all fields specified."""
        request = db_models.BackendRequest.objects.create(
            relation_id=5,
            hostname_acls=["example.com", "app.example.com"],
            backend_name="web-backend",
            paths=["/api", "/health"],
            port=8080,
            status=db_models.REQUEST_STATUS_ACCEPTED,
        )
        self.assertEqual(request.relation_id, 5)
        self.assertEqual(request.hostname_acls, ["example.com", "app.example.com"])
        self.assertEqual(request.backend_name, "web-backend")
        self.assertEqual(request.paths, ["/api", "/health"])
        self.assertEqual(request.port, 8080)
        self.assertEqual(request.status, db_models.REQUEST_STATUS_ACCEPTED)

    def test_to_jsonable(self):
        """Test serialisation to a JSON-compatible dict."""
        request = db_models.BackendRequest.objects.create(
            relation_id=2,
            hostname_acls=["host.example.com"],
            backend_name="backend-a",
            paths=["/v1"],
            port=443,
        )
        data = request.to_dict()
        self.assertEqual(data["id"], request.pk)
        self.assertEqual(data["relation_id"], 2)
        self.assertEqual(data["hostname_acls"], ["host.example.com"])
        self.assertEqual(data["backend_name"], "backend-a")
        self.assertEqual(data["paths"], ["/v1"])
        self.assertEqual(data["port"], 443)
        self.assertEqual(data["status"], db_models.REQUEST_STATUS_PENDING)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)
