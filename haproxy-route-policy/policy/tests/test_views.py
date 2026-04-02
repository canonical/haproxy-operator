# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the policy REST API views."""

import uuid

from django.test import TestCase
from rest_framework.test import APIClient

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
        self.assertEqual(data["id"], self.backend_request.pk)
        self.assertEqual(data["backend_name"], "detail-backend")

    def test_get_not_found(self):
        """GET returns 404 for a non-existent ID."""
        response = self.client.get("/api/v1/requests/99999")
        self.assertEqual(response.status_code, 404)

    def test_delete_existing(self):
        """DELETE removes the request and returns 204."""
        pk = self.backend_request.pk
        response = self.client.delete(f"/api/v1/requests/{pk}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(db_models.BackendRequest.objects.filter(pk=pk).exists())

    def test_delete_nonexistent(self):
        """DELETE on a non-existent ID still returns 204 (idempotent)."""
        response = self.client.delete("/api/v1/requests/99999")
        self.assertEqual(response.status_code, 204)


class TestListCreateRulesView(TestCase):
    """Tests for GET /api/v1/rules and POST /api/v1/rules."""

    def setUp(self):
        """Set up the API client."""
        self.client = APIClient()

    def test_list_empty(self):
        """GET returns an empty list when no rules exist."""
        response = self.client.get("/api/v1/rules")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_returns_all_ordered_by_priority(self):
        """GET returns all rules ordered by descending priority."""
        rule_low = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            value={"hostnames": ["example.com"], "paths": ["/api"]},
            action=db_models.RULE_ACTION_ALLOW,
            priority=0,
        )
        rule_low.full_clean()
        rule_low.save()
        rule_high = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            value={"hostnames": ["example.org"], "paths": ["/admin"]},
            action=db_models.RULE_ACTION_DENY,
            priority=10,
        )
        rule_high.full_clean()
        rule_high.save()

        response = self.client.get("/api/v1/rules")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        # Higher priority should come first
        self.assertEqual(data[0]["priority"], 10)
        self.assertEqual(data[1]["priority"], 0)

    def test_create_hostname_and_path_match_rule(self):
        """POST creates a hostname_and_path_match rule."""
        payload = {
            "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            "value": {"hostnames": ["example.com"], "paths": ["/api"]},
            "action": db_models.RULE_ACTION_DENY,
            "priority": 5,
            "comment": "Block example.com/api",
        }
        response = self.client.post("/api/v1/rules", data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["kind"], db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH)
        self.assertEqual(
            data["value"], {"hostnames": ["example.com"], "paths": ["/api"]}
        )
        self.assertEqual(data["action"], db_models.RULE_ACTION_DENY)
        self.assertEqual(data["priority"], 5)
        self.assertEqual(data["comment"], "Block example.com/api")
        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertEqual(db_models.Rule.objects.count(), 1)

    def test_create_rule_with_defaults(self):
        """POST creates a rule with default priority and comment."""
        payload = {
            "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            "value": {"hostnames": ["example.com"], "paths": ["/api"]},
            "action": db_models.RULE_ACTION_DENY,
        }
        response = self.client.post("/api/v1/rules", data=payload, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["priority"], 0)
        self.assertEqual(data["comment"], "")

    def test_create_rule_missing_required_fields(self):
        """POST returns 400 when required fields are missing."""
        payload = {"kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH}
        response = self.client.post("/api/v1/rules", data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_rule_invalid_kind(self):
        """POST returns 400 when kind is invalid."""
        payload = {
            "kind": "invalid_kind",
            "value": 1,
            "action": db_models.RULE_ACTION_ALLOW,
        }
        response = self.client.post("/api/v1/rules", data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_rule_invalid_value_for_kind(self):
        """POST returns 400 when value doesn't match kind requirements."""
        payload = {
            "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            "value": "not-a-dict",
            "action": db_models.RULE_ACTION_DENY,
        }
        response = self.client.post("/api/v1/rules", data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_rule_rejects_non_dict(self):
        """POST returns 400 when the body is not a JSON object."""
        response = self.client.post(
            "/api/v1/rules", data=[{"kind": "test"}], format="json"
        )
        self.assertEqual(response.status_code, 400)


class TestRuleDetailView(TestCase):
    """Tests for GET, PUT, DELETE /api/v1/rules/<id>."""

    def setUp(self):
        """Set up the API client and a sample rule."""
        self.client = APIClient()
        self.rule = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            value={"hostnames": ["example.com"], "paths": ["/api"]},
            action=db_models.RULE_ACTION_DENY,
            priority=1,
            comment="Test rule",
        )
        self.rule.full_clean()
        self.rule.save()

    def test_get_existing(self):
        """GET returns the rule matching the given ID."""
        response = self.client.get(f"/api/v1/rules/{self.rule.pk}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.rule.pk))
        self.assertEqual(data["kind"], db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH)

    def test_get_not_found(self):
        """GET returns 404 for a non-existent rule ID."""
        fake_id = uuid.uuid4()
        response = self.client.get(f"/api/v1/rules/{fake_id}")
        self.assertEqual(response.status_code, 404)

    def test_update_rule(self):
        """PUT updates the rule fields."""
        payload = {
            "priority": 10,
            "comment": "Updated comment",
            "action": db_models.RULE_ACTION_ALLOW,
        }
        response = self.client.put(
            f"/api/v1/rules/{self.rule.pk}", data=payload, format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["priority"], 10)
        self.assertEqual(data["comment"], "Updated comment")
        self.assertEqual(data["action"], db_models.RULE_ACTION_ALLOW)
        # Unchanged fields remain the same
        self.assertEqual(data["kind"], db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH)
        self.assertEqual(
            data["value"], {"hostnames": ["example.com"], "paths": ["/api"]}
        )

    def test_update_nonexistent(self):
        """PUT returns 404 for a non-existent rule ID."""
        fake_id = uuid.uuid4()
        response = self.client.put(
            f"/api/v1/rules/{fake_id}", data={"priority": 5}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_existing(self):
        """DELETE removes the rule and returns 204."""
        pk = self.rule.pk
        response = self.client.delete(f"/api/v1/rules/{pk}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(db_models.Rule.objects.filter(pk=pk).exists())

    def test_delete_nonexistent(self):
        """DELETE on a non-existent rule ID still returns 204 (idempotent)."""
        fake_id = uuid.uuid4()
        response = self.client.delete(f"/api/v1/rules/{fake_id}")
        self.assertEqual(response.status_code, 204)
