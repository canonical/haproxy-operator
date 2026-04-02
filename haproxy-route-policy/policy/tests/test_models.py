# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the BackendRequest and Rule models."""

from django.test import TestCase
from django.core.exceptions import ValidationError

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
        self.assertEqual(request.status, db_models.REQUEST_STATUS_PENDING)
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
            status=db_models.REQUEST_STATUS_ACCEPTED,
        )
        self.assertEqual(request.relation_id, 5)
        self.assertEqual(request.hostname_acls, ["example.com", "app.example.com"])
        self.assertEqual(request.backend_name, "web-backend")
        self.assertEqual(request.paths, ["/api", "/health"])
        self.assertEqual(request.port, 443)
        self.assertEqual(request.status, db_models.REQUEST_STATUS_ACCEPTED)


class TestRuleModel(TestCase):
    """Tests for Rule model creation, serialisation, and validation."""

    def test_create_hostname_and_path_match_rule(self):
        """Test creating a hostname_and_path_match rule with valid data."""
        rule = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            value={"hostnames": ["example.com"], "paths": ["/api"]},
            action=db_models.RULE_ACTION_DENY,
            priority=1,
            comment="Deny example.com/api",
        )
        rule.full_clean()
        rule.save()

        self.assertIsNotNone(rule.id)
        self.assertEqual(rule.kind, db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH)
        self.assertEqual(rule.value, {"hostnames": ["example.com"], "paths": ["/api"]})
        self.assertEqual(rule.action, db_models.RULE_ACTION_DENY)
        self.assertEqual(rule.priority, 1)
        self.assertEqual(rule.comment, "Deny example.com/api")
        self.assertIsNotNone(rule.created_at)
        self.assertIsNotNone(rule.updated_at)

    def test_create_rule_defaults(self):
        """Test that default values are set correctly."""
        rule = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            value={"hostnames": ["test.com"], "paths": []},
            action=db_models.RULE_ACTION_ALLOW,
        )
        rule.full_clean()
        rule.save()

        self.assertEqual(rule.priority, 0)
        self.assertEqual(rule.comment, "")

    def test_to_dict(self):
        """Test serialisation to a JSON-compatible dict."""
        rule = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            value={"hostnames": ["example.com"], "paths": []},
            action=db_models.RULE_ACTION_DENY,
            priority=5,
            comment="Test rule",
        )
        rule.full_clean()
        rule.save()

        data = rule.to_dict()
        self.assertEqual(data["id"], str(rule.id))
        self.assertEqual(data["kind"], db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH)
        self.assertEqual(data["value"], {"hostnames": ["example.com"], "paths": []})
        self.assertEqual(data["action"], db_models.RULE_ACTION_DENY)
        self.assertEqual(data["priority"], 5)
        self.assertEqual(data["comment"], "Test rule")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_invalid_kind_rejected(self):
        """Test that an invalid kind value is rejected."""
        rule = db_models.Rule(
            kind="invalid_kind",
            value=1,
            action=db_models.RULE_ACTION_ALLOW,
        )
        with self.assertRaises(ValidationError):
            rule.full_clean()
