# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the policy REST API views."""

from django.test import TestCase
from rest_framework.test import APIClient
import uuid
from policy import db_models


class TestListCreateRequestsView(TestCase):
    """Tests for GET /api/v1/requests and POST /api/v1/requests."""

    def setUp(self):
        """Set up the API client."""
        self.client = APIClient()

    def test_list_empty(self):
        """GET returns an empty list when no requests exist."""
        response = self.client.get("/api/v1/requests")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_returns_all(self):
        """GET returns all requests."""
        db_models.BackendRequest.objects.create(
            relation_id=1, backend_name="a", port=443
        )
        db_models.BackendRequest.objects.create(
            relation_id=2, backend_name="b", port=443
        )
        response = self.client.get("/api/v1/requests")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["backend_name"], "a")
        self.assertEqual(data[1]["backend_name"], "b")

    def test_list_filter_by_status(self):
        """GET with ?status= filters results."""
        db_models.BackendRequest.objects.create(
            relation_id=1,
            backend_name="a",
            status=db_models.REQUEST_STATUS_PENDING,
            port=443,
        )
        db_models.BackendRequest.objects.create(
            relation_id=2,
            backend_name="b",
            status=db_models.REQUEST_STATUS_ACCEPTED,
            port=443,
        )
        response = self.client.get("/api/v1/requests?status=accepted")
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["backend_name"], "b")

    def test_bulk_create(self):
        """POST creates multiple requests and returns them."""
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
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["backend_name"], "backend-1")
        self.assertEqual(data[0]["status"], "pending")
        self.assertEqual(data[0]["hostname_acls"], ["example.com"])
        self.assertEqual(data[0]["paths"], ["/api"])
        self.assertEqual(data[0]["port"], 443)
        self.assertEqual(data[1]["backend_name"], "backend-2")
        self.assertEqual(data[1]["hostname_acls"], [])
        self.assertEqual(data[1]["paths"], [])
        self.assertEqual(data[1]["port"], 443)
        self.assertEqual(db_models.BackendRequest.objects.count(), 2)

    def test_bulk_create_rejects_non_list(self):
        """POST returns 400 when the body is not a list."""
        response = self.client.post(
            "/api/v1/requests",
            data={"relation_id": 1, "backend_name": "x", "port": 443},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class TestRequestDetailView(TestCase):
    """Tests for GET /api/v1/requests/<id> and DELETE /api/v1/requests/<id>."""

    def setUp(self):
        """Set up the API client and a sample request."""
        self.client = APIClient()
        self.backend_request = db_models.BackendRequest.objects.create(
            relation_id=10,
            hostname_acls=["host.test"],
            backend_name="detail-backend",
            port=443,
        )

    def test_get_existing(self):
        """GET returns the request matching the given ID."""
        response = self.client.get(f"/api/v1/requests/{self.backend_request.pk}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.backend_request.pk))
        self.assertEqual(data["backend_name"], "detail-backend")

    def test_get_not_found(self):
        """GET returns 404 for a non-existent ID."""
        response = self.client.get(f"/api/v1/requests/{uuid.uuid4()}")
        self.assertEqual(response.status_code, 404)

    def test_delete_existing(self):
        """DELETE removes the request and returns 204."""
        pk = self.backend_request.pk
        response = self.client.delete(f"/api/v1/requests/{pk}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(db_models.BackendRequest.objects.filter(pk=pk).exists())

    def test_delete_nonexistent(self):
        """DELETE on a non-existent ID still returns 204 (idempotent)."""
        response = self.client.delete(f"/api/v1/requests/{uuid.uuid4()}")
        self.assertEqual(response.status_code, 204)


class TestStatusFilterSanitization(TestCase):
    """Tests for status query parameter validation on GET /api/v1/requests."""

    def setUp(self):
        """Set up the API client."""
        self.client = APIClient()

    def test_valid_status_filters(self):
        """Valid status values should return 200."""
        valid_statuses = ["pending", "accepted", "rejected"]
        for status in valid_statuses:
            with self.subTest(status=status):
                response = self.client.get(f"/api/v1/requests?status={status}")
                self.assertEqual(response.status_code, 200)

    def test_invalid_status_filters(self):
        """Invalid status values should return 400."""
        invalid_statuses = [
            "invalid",
            "PENDING",
            "Accepted",
            "unknown",
            "' OR 1=1 --",
            "<script>alert(1)</script>",
            "pending; DROP TABLE",
        ]
        for status in invalid_statuses:
            with self.subTest(status=status):
                response = self.client.get(f"/api/v1/requests?status={status}")
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())


class TestPkValidation(TestCase):
    """Tests for pk (UUID) validation on GET/DELETE /api/v1/requests/<pk>."""

    def setUp(self):
        """Set up the API client."""
        self.client = APIClient()

    def test_get_invalid_pk_returns_400(self):
        """GET with an invalid UUID pk should return 400."""
        invalid_pks = [
            "not-a-uuid",
            "12345",
            "' OR 1=1 --",
            " ",
        ]
        for pk in invalid_pks:
            with self.subTest(pk=pk):
                response = self.client.get(f"/api/v1/requests/{pk}")
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())

    def test_delete_invalid_pk_returns_204(self):
        """DELETE with an invalid UUID pk should still return 204 (idempotent)."""
        invalid_pks = [
            "not-a-uuid",
            "12345",
            "' OR 1=1 --",
        ]
        for pk in invalid_pks:
            with self.subTest(pk=pk):
                response = self.client.delete(f"/api/v1/requests/{pk}")
                self.assertEqual(response.status_code, 204)
