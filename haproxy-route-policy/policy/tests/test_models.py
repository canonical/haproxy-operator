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
    """Tests for Rule model creation, serialization, and validation."""

    def test_create_rule_defaults(self):
        """Test that default values are set correctly."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "parameters": {"hostnames": ["test.com"], "paths": []},
                "action": db_models.RULE_ACTION_ALLOW,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        rule = serializer.save()

        self.assertEqual(rule.priority, 0)
        self.assertEqual(rule.comment, "")

    def test_create_hostname_and_path_match_rule(self):
        """Test creating a hostname_and_path_match rule with valid data."""
        serializer = serializers.RuleSerializer(
            data={
                "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                "parameters": {"hostnames": ["example.com"], "paths": ["/api"]},
                "action": db_models.RULE_ACTION_DENY,
                "priority": 1,
                "comment": "Deny example.com/api",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        rule = serializer.save()

        self.assertIsNotNone(rule.id)
        self.assertEqual(rule.kind, db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH)
        self.assertEqual(
            rule.parameters, {"hostnames": ["example.com"], "paths": ["/api"]}
        )
        self.assertEqual(rule.action, db_models.RULE_ACTION_DENY)
        self.assertEqual(rule.priority, 1)
        self.assertEqual(rule.comment, "Deny example.com/api")
        self.assertIsNotNone(rule.created_at)
        self.assertIsNotNone(rule.updated_at)

    def test_valid_rule_data_accepted(self):
        """Valid rule data should pass serializer validation."""
        valid_cases = [
            (
                "valid hostnames",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {
                        "hostnames": ["example.com", "sub.example.org"],
                        "paths": [],
                    },
                    "action": db_models.RULE_ACTION_ALLOW,
                },
            ),
            (
                "empty hostnames",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {"hostnames": [], "paths": []},
                    "action": db_models.RULE_ACTION_ALLOW,
                },
            ),
            (
                "valid paths",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {
                        "hostnames": ["example.com"],
                        "paths": ["/api", "/health"],
                    },
                    "action": db_models.RULE_ACTION_ALLOW,
                },
            ),
            (
                "empty paths",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {"hostnames": ["example.com"], "paths": []},
                    "action": db_models.RULE_ACTION_ALLOW,
                },
            ),
            (
                "both valid hostnames and paths",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {
                        "hostnames": ["example.com", "app.example.com"],
                        "paths": ["/api", "/v1/health"],
                    },
                    "action": db_models.RULE_ACTION_DENY,
                    "priority": 3,
                    "comment": "Block specific routes",
                },
            ),
        ]
        for label, data in valid_cases:
            with self.subTest(label=label):
                serializer = serializers.RuleSerializer(data=data)
                self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_rule_data_rejected(self):
        """Invalid rule data should fail serializer validation."""
        invalid_cases = [
            (
                "invalid kind",
                {
                    "kind": "invalid_kind",
                    "parameters": 1,
                    "action": db_models.RULE_ACTION_ALLOW,
                },
                {"field": "kind"},
            ),
            (
                "invalid action",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {"hostnames": ["example.com"], "paths": []},
                    "action": "invalid_action",
                },
                {"field": "action"},
            ),
            (
                "parameters must be dict — string given",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": "not-a-dict",
                    "action": db_models.RULE_ACTION_DENY,
                },
                {
                    "field": "non_field_errors",
                    "message": "parameters field must be a JSON object",
                },
            ),
            (
                "parameters must be dict — list given",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": ["not", "a", "dict"],
                    "action": db_models.RULE_ACTION_DENY,
                },
                {
                    "field": "non_field_errors",
                    "message": "parameters field must be a JSON object",
                },
            ),
            (
                "parameters must be dict — int given",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": 42,
                    "action": db_models.RULE_ACTION_DENY,
                },
                {
                    "field": "non_field_errors",
                    "message": "parameters field must be a JSON object",
                },
            ),
            (
                "invalid hostname",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {
                        "hostnames": ["not a valid hostname!!!"],
                        "paths": [],
                    },
                    "action": db_models.RULE_ACTION_DENY,
                },
                {"message": "Invalid hostname"},
            ),
            (
                "multiple invalid hostnames",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {
                        "hostnames": ["valid.com", "bad host", "also bad!"],
                        "paths": [],
                    },
                    "action": db_models.RULE_ACTION_DENY,
                },
                {"message_contains": ["bad host", "also bad!"]},
            ),
            (
                "path without leading slash",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {"hostnames": ["example.com"], "paths": ["api/v1"]},
                    "action": db_models.RULE_ACTION_DENY,
                },
                {"message": "Invalid path"},
            ),
            (
                "non-string path",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {"hostnames": ["example.com"], "paths": [123]},
                    "action": db_models.RULE_ACTION_DENY,
                },
                {},
            ),
            (
                "multiple invalid paths",
                {
                    "kind": db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
                    "parameters": {"hostnames": [], "paths": ["no-slash", "also-bad"]},
                    "action": db_models.RULE_ACTION_DENY,
                },
                {"message_contains": ["no-slash", "also-bad"]},
            ),
        ]
        for label, data, checks in invalid_cases:
            with self.subTest(label=label):
                serializer = serializers.RuleSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                errors_str = str(serializer.errors)
                if "field" in checks:
                    self.assertIn(checks["field"], serializer.errors)
                if "message" in checks:
                    self.assertIn(checks["message"], errors_str)
                if "message_contains" in checks:
                    for fragment in checks["message_contains"]:
                        self.assertIn(fragment, errors_str)


class TestValidatePort(TestCase):
    """Tests for the validate_port validator."""

    def test_valid_ports(self):
        """Valid TCP port numbers should not raise."""
        valid_ports = [1, 80, 443, 8080, 65535]
        for port in valid_ports:
            with self.subTest(port=port):
                db_models.validate_port(port)

    def test_invalid_ports(self):
        """Out-of-range and wrong-type values should raise ValidationError."""
        invalid_ports = [
            (0, "below minimum"),
            (-1, "negative"),
            (65536, "above maximum"),
            (100000, "way above maximum"),
            ("443", "string"),
            (44.3, "float"),
            (None, "None"),
        ]
        for value, label in invalid_ports:
            with self.subTest(value=value, label=label):
                with self.assertRaises(ValidationError):
                    db_models.validate_port(value)


class TestValidatePaths(TestCase):
    """Tests for the validate_paths validator."""

    def test_valid_paths(self):
        """Valid path lists should not raise."""
        valid_cases = [
            ([], "empty list"),
            (["/"], "root path"),
            (["/api"], "single path"),
            (["/api", "/health", "/status"], "multiple paths"),
            (["/api/v1/requests"], "nested path"),
        ]
        for paths, label in valid_cases:
            with self.subTest(paths=paths, label=label):
                db_models.validate_paths(paths)

    def test_invalid_paths(self):
        """Invalid path values should raise ValidationError."""
        invalid_cases = [
            ("not-a-list", "string instead of list"),
            (None, "None"),
            (123, "integer"),
            (["no-leading-slash"], "missing leading slash"),
            (["api/v1"], "relative path"),
            ([123], "non-string element"),
            ([None], "None element"),
            (["/valid", "invalid"], "mixed valid and invalid"),
        ]
        for value, label in invalid_cases:
            with self.subTest(value=value, label=label):
                with self.assertRaises(ValidationError):
                    db_models.validate_paths(value)
