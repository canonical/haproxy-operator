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
            relation_id=1, backend_name="my-backend", port=443
        )
        self.assertEqual(request.relation_id, 1)
        self.assertEqual(request.backend_name, "my-backend")
        self.assertEqual(request.hostname_acls, [])
        self.assertEqual(request.paths, [])
        self.assertEqual(request.status, db_models.RequestStatus.PENDING)
        self.assertEqual(request.port, 443)
        self.assertIsNotNone(request.created_at)
        self.assertIsNotNone(request.updated_at)

    def test_create_with_all_fields(self):
        """Test creating a request with all fields specified."""
        request = db_models.BackendRequest.objects.create(
            relation_id=5,
            hostname_acls=["example.com", "app.example.com"],
            backend_name="web-backend",
            paths=["/api", "/health"],
            port=443,
            status=db_models.RequestStatus.ACCEPTED,
        )
        self.assertEqual(request.relation_id, 5)
        self.assertEqual(request.hostname_acls, ["example.com", "app.example.com"])
        self.assertEqual(request.backend_name, "web-backend")
        self.assertEqual(request.paths, ["/api", "/health"])
        self.assertEqual(request.port, 443)
        self.assertEqual(request.status, db_models.RequestStatus.ACCEPTED)
