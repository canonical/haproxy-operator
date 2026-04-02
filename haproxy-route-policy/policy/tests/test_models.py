# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the BackendRequest and Rule models."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from policy import db_models, serializers


class TestBackendRequestModel(TestCase):
    """Tests for BackendRequest model creation and serialization."""

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
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["example.com"], "paths": ["/api"]},
                "action": db_models.RULE_ACTION_DENY,
                "priority": 1,
                "comment": "Deny example.com/api",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        rule = serializer.save()

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
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["test.com"], "paths": []},
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        rule = serializer.save()

        self.assertEqual(rule.priority, 0)
        self.assertEqual(rule.comment, "")

    def test_invalid_kind_rejected(self):
        """Test that an invalid kind value is rejected."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": "invalid_kind",
                "value": 1,
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("kind", serializer.errors)

    def test_invalid_action_rejected(self):
        """Test that an invalid action value is rejected."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["example.com"], "paths": []},
                "action": "invalid_action",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("action", serializer.errors)

    def test_hostname_and_path_match_value_must_be_dict(self):
        """Test that hostname_and_path_match rules require a dict value."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": "not-a-dict",
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn(
            "value field must be a JSON object",
            str(serializer.errors["non_field_errors"]),
        )

    def test_hostname_and_path_match_value_list_rejected(self):
        """Test that hostname_and_path_match rules reject a list value."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": ["not", "a", "dict"],
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn(
            "value field must be a JSON object",
            str(serializer.errors["non_field_errors"]),
        )

    def test_hostname_and_path_match_value_int_rejected(self):
        """Test that hostname_and_path_match rules reject an integer value."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": 42,
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn(
            "value field must be a JSON object",
            str(serializer.errors["non_field_errors"]),
        )

    def test_hostname_and_path_match_invalid_hostname(self):
        """Test that invalid hostnames are rejected in hostname_and_path_match rules."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["not a valid hostname!!!"], "paths": []},
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("Invalid hostname", str(serializer.errors))

    def test_hostname_and_path_match_multiple_invalid_hostnames(self):
        """Test that multiple invalid hostnames are reported."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {
                    "hostnames": ["valid.com", "bad host", "also bad!"],
                    "paths": [],
                },
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        errors_str = str(serializer.errors)
        self.assertIn("bad host", errors_str)
        self.assertIn("also bad!", errors_str)

    def test_hostname_and_path_match_valid_hostnames_accepted(self):
        """Test that valid hostnames pass validation."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {
                    "hostnames": ["example.com", "sub.example.org"],
                    "paths": [],
                },
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_hostname_and_path_match_empty_hostnames_accepted(self):
        """Test that an empty hostnames list passes validation."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": [], "paths": []},
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_hostname_and_path_match_invalid_path_not_starting_with_slash(self):
        """Test that paths not starting with / are rejected."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["example.com"], "paths": ["api/v1"]},
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("Invalid path", str(serializer.errors))

    def test_hostname_and_path_match_invalid_path_non_string(self):
        """Test that non-string paths are rejected."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["example.com"], "paths": [123]},
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_hostname_and_path_match_valid_paths_accepted(self):
        """Test that valid paths starting with / pass validation."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {
                    "hostnames": ["example.com"],
                    "paths": ["/api", "/health"],
                },
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_hostname_and_path_match_empty_paths_accepted(self):
        """Test that an empty paths list passes validation."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": ["example.com"], "paths": []},
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_hostname_and_path_match_multiple_invalid_paths(self):
        """Test that multiple invalid paths are reported."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {"hostnames": [], "paths": ["no-slash", "also-bad"]},
                "action": db_models.RULE_ACTION_DENY,
            }
        )
        self.assertFalse(serializer.is_valid())
        errors_str = str(serializer.errors)
        self.assertIn("no-slash", errors_str)
        self.assertIn("also-bad", errors_str)

    def test_hostname_and_path_match_both_valid_hostnames_and_paths(self):
        """Test that a rule with both valid hostnames and paths passes."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "value": {
                    "hostnames": ["example.com", "app.example.com"],
                    "paths": ["/api", "/v1/health"],
                },
                "action": db_models.RULE_ACTION_DENY,
                "priority": 3,
                "comment": "Block specific routes",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        rule = serializer.save()
        self.assertIsNotNone(rule.id)
