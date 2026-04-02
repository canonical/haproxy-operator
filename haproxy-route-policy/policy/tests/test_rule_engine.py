# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the rule matching engine."""

from django.test import TestCase

from policy import db_models
from policy.rule_engine import evaluate_request, _hostname_and_path_match


class TestHostnameAndPathMatch(TestCase):
    """Tests for the _hostname_and_path_match matching function."""

    def _make_request(self, hostname_acls=None, paths=None):
        """Create and save a BackendRequest with the given hostnames and paths."""
        return db_models.BackendRequest.objects.create(
            relation_id=1,
            backend_name="test-backend",
            hostname_acls=hostname_acls or [],
            paths=paths or [],
            port=443,
        )

    def _make_rule(self, hostnames=None, paths=None, action="deny", priority=0):
        """Create and save a Rule with hostname_and_path_match kind."""
        rule = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            parameters={"hostnames": hostnames or [], "paths": paths or []},
            action=action,
            priority=priority,
        )
        rule.save()
        return rule

    def test_exact_hostname_match(self):
        """Rule matches when hostnames overlap exactly."""
        rule = self._make_rule(hostnames=["example.com"])
        request = self._make_request(hostname_acls=["example.com"])
        self.assertTrue(_hostname_and_path_match(rule, request))

    def test_hostname_no_overlap(self):
        """Rule does not match when hostnames don't overlap."""
        rule = self._make_rule(hostnames=["example.com"])
        request = self._make_request(hostname_acls=["other.com"])
        self.assertFalse(_hostname_and_path_match(rule, request))

    def test_hostname_partial_overlap(self):
        """Rule matches when at least one hostname overlaps."""
        rule = self._make_rule(hostnames=["example.com", "other.com"])
        request = self._make_request(hostname_acls=["example.com", "third.com"])
        self.assertTrue(_hostname_and_path_match(rule, request))

    def test_empty_rule_hostnames_no_match(self):
        """Rule with empty hostnames never matches."""
        rule = self._make_rule(hostnames=[])
        request = self._make_request(hostname_acls=["example.com"])
        self.assertFalse(_hostname_and_path_match(rule, request))

    def test_empty_request_hostnames_no_match(self):
        """Request with empty hostname_acls doesn't match a hostname rule."""
        rule = self._make_rule(hostnames=["example.com"])
        request = self._make_request(hostname_acls=[])
        self.assertFalse(_hostname_and_path_match(rule, request))

    def test_empty_rule_paths_matches_all_paths(self):
        """Rule with empty paths list matches any request paths (wildcard)."""
        rule = self._make_rule(hostnames=["example.com"], paths=[])
        request = self._make_request(
            hostname_acls=["example.com"], paths=["/api", "/health"]
        )
        self.assertTrue(_hostname_and_path_match(rule, request))

    def test_empty_rule_paths_matches_empty_request_paths(self):
        """Rule with empty paths matches requests with no paths."""
        rule = self._make_rule(hostnames=["example.com"], paths=[])
        request = self._make_request(hostname_acls=["example.com"], paths=[])
        self.assertTrue(_hostname_and_path_match(rule, request))

    def test_path_overlap(self):
        """Rule matches when paths overlap."""
        rule = self._make_rule(hostnames=["example.com"], paths=["/api"])
        request = self._make_request(
            hostname_acls=["example.com"], paths=["/api", "/health"]
        )
        self.assertTrue(_hostname_and_path_match(rule, request))

    def test_path_no_overlap(self):
        """Rule does not match when paths don't overlap."""
        rule = self._make_rule(hostnames=["example.com"], paths=["/admin"])
        request = self._make_request(
            hostname_acls=["example.com"], paths=["/api", "/health"]
        )
        self.assertFalse(_hostname_and_path_match(rule, request))

    def test_rule_paths_set_but_request_paths_empty(self):
        """Rule with specific paths does not match request with no paths."""
        rule = self._make_rule(hostnames=["example.com"], paths=["/api"])
        request = self._make_request(hostname_acls=["example.com"], paths=[])
        self.assertFalse(_hostname_and_path_match(rule, request))

    def test_hostname_match_but_path_mismatch(self):
        """Rule doesn't match when hostnames match but paths don't."""
        rule = self._make_rule(hostnames=["example.com"], paths=["/admin"])
        request = self._make_request(hostname_acls=["example.com"], paths=["/api"])
        self.assertFalse(_hostname_and_path_match(rule, request))

    def test_multiple_hostnames_and_paths(self):
        """Rule matches with multiple hostnames and paths that overlap."""
        rule = self._make_rule(
            hostnames=["example.com", "other.com"],
            paths=["/api", "/v2"],
        )
        request = self._make_request(
            hostname_acls=["other.com"], paths=["/v2", "/health"]
        )
        self.assertTrue(_hostname_and_path_match(rule, request))


class TestEvaluateRequest(TestCase):
    """Tests for the evaluate_request function."""

    def _make_request(self, hostname_acls=None, paths=None):
        """Create and save a BackendRequest."""
        return db_models.BackendRequest.objects.create(
            relation_id=1,
            backend_name="test-backend",
            hostname_acls=hostname_acls or [],
            paths=paths or [],
            port=443,
        )

    def _make_rule(self, hostnames=None, paths=None, action="deny", priority=0):
        """Create and save a hostname_and_path_match Rule."""
        rule = db_models.Rule(
            kind=db_models.RULE_KIND_HOSTNAME_AND_PATH_MATCH,
            parameters={"hostnames": hostnames or [], "paths": paths or []},
            action=action,
            priority=priority,
        )
        rule.save()
        return rule

    def test_no_rules_returns_pending(self):
        """Request stays pending when no rules exist."""
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_PENDING)

    def test_no_matching_rules_returns_pending(self):
        """Request stays pending when no rules match."""
        self._make_rule(hostnames=["other.com"], action=db_models.RULE_ACTION_DENY)
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_PENDING)

    def test_single_allow_rule_accepts(self):
        """Request is accepted when a single allow rule matches."""
        self._make_rule(hostnames=["example.com"], action=db_models.RULE_ACTION_ALLOW)
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_ACCEPTED)

    def test_single_deny_rule_rejects(self):
        """Request is rejected when a single deny rule matches."""
        self._make_rule(hostnames=["example.com"], action=db_models.RULE_ACTION_DENY)
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_REJECTED)

    def test_deny_wins_over_allow_at_same_priority(self):
        """Deny rule takes precedence over allow rule at the same priority."""
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=0,
        )
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_DENY,
            priority=0,
        )
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_REJECTED)

    def test_higher_priority_evaluated_first(self):
        """Higher priority rules are evaluated before lower priority ones."""
        # Priority 1: allow example.com/client
        self._make_rule(
            hostnames=["example.com"],
            paths=["/client"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=1,
        )
        # Priority 0: deny example.com (all paths)
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_DENY,
            priority=0,
        )
        request = self._make_request(hostname_acls=["example.com"], paths=["/client"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_ACCEPTED)

    def test_spec_example_client_allowed(self):
        """Spec example: request for example.com/client is allowed.

        Rules:
            Rule 1: deny example.com (all paths), priority=0
            Rule 2: allow example.com /api, priority=0
            Rule 3: allow example.com /client, priority=1
        """
        # Rule 1
        self._make_rule(
            hostnames=["example.com"],
            paths=[],
            action=db_models.RULE_ACTION_DENY,
            priority=0,
        )
        # Rule 2
        self._make_rule(
            hostnames=["example.com"],
            paths=["/api"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=0,
        )
        # Rule 3
        self._make_rule(
            hostnames=["example.com"],
            paths=["/client"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=1,
        )
        request = self._make_request(hostname_acls=["example.com"], paths=["/client"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_ACCEPTED)

    def test_spec_example_api_denied(self):
        """Spec example: request for example.com/api is denied.

        Rules:
            Rule 1: deny example.com (all paths), priority=0
            Rule 2: allow example.com /api, priority=0
            Rule 3: allow example.com /client, priority=1
        """
        # Rule 1
        self._make_rule(
            hostnames=["example.com"],
            paths=[],
            action=db_models.RULE_ACTION_DENY,
            priority=0,
        )
        # Rule 2
        self._make_rule(
            hostnames=["example.com"],
            paths=["/api"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=0,
        )
        # Rule 3
        self._make_rule(
            hostnames=["example.com"],
            paths=["/client"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=1,
        )
        request = self._make_request(hostname_acls=["example.com"], paths=["/api"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_REJECTED)

    def test_lower_priority_not_reached_if_higher_matches(self):
        """If a higher priority group matches, lower priority groups are skipped."""
        # Priority 5: allow example.com
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=5,
        )
        # Priority 0: deny example.com
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_DENY,
            priority=0,
        )
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_ACCEPTED)

    def test_only_matching_rules_affect_outcome(self):
        """Non-matching rules at the same priority don't affect the result."""
        # Deny other.com at priority 0
        self._make_rule(
            hostnames=["other.com"],
            action=db_models.RULE_ACTION_DENY,
            priority=0,
        )
        # Allow example.com at priority 0
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=0,
        )
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_ACCEPTED)

    def test_multiple_priority_groups_fallthrough(self):
        """If highest priority group has no match, fall through to next."""
        # Priority 10: deny other.com (doesn't match)
        self._make_rule(
            hostnames=["other.com"],
            action=db_models.RULE_ACTION_DENY,
            priority=10,
        )
        # Priority 0: allow example.com
        self._make_rule(
            hostnames=["example.com"],
            action=db_models.RULE_ACTION_ALLOW,
            priority=0,
        )
        request = self._make_request(hostname_acls=["example.com"])
        self.assertEqual(evaluate_request(request), db_models.REQUEST_STATUS_ACCEPTED)
