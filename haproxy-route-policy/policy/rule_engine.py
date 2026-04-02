# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Rule matching engine for evaluating backend requests against rules.

Rules are evaluated following these principles:
    P1: Rules are grouped by priority and evaluated starting from the highest
        priority group.
    P2: Within the same priority group, "deny" rules take precedence over
        "allow" rules.

If no rules match a request, its status remains "pending".
"""

import logging
from itertools import groupby
from policy.db_models import (
    BackendRequest,
    Rule,
    RULE_ACTION_ALLOW,
    RULE_ACTION_DENY,
    RULE_KIND_HOSTNAME_AND_PATH_MATCH,
    REQUEST_STATUS_ACCEPTED,
    REQUEST_STATUS_REJECTED,
    REQUEST_STATUS_PENDING,
)

logger = logging.getLogger(__name__)


def _hostname_and_path_match(rule: Rule, request: BackendRequest) -> bool:
    """Check if a hostname_and_path_match rule matches a backend request.

    A rule matches if:
        1. Any of the rule's `hostnames` appear in the request's `hostname_acls`
           if `hostnames` is not empty.
        2. Any of the rule's `paths` appear in the request's `paths`
           if `paths` is not empty..

    Args:
        rule: The rule to check.
        request: The backend request to evaluate.

    Returns:
        True if the rule matches the request, False otherwise.
    """
    rule_hostnames: list = rule.parameters.get("hostnames", [])
    rule_paths: list = rule.parameters.get("paths", [])

    hostname_matched = set(request.hostname_acls).intersection(set(rule_hostnames))
    path_matched = set(request.paths).intersection(set(rule_paths))
    if not rule_hostnames and not rule_paths:
        return False
    if not rule_hostnames:
        return bool(path_matched)
    if not rule_paths:
        return bool(hostname_matched)
    return bool(hostname_matched) and bool(path_matched)


def evaluate_request(request: BackendRequest) -> str:
    """Evaluate a backend request against all rules and return the resulting status.

    Rules are fetched from the database, ordered by descending priority.
    They are grouped by priority level and evaluated from highest to lowest.

    Within the same priority group:
        - If any "deny" rule matches, the request is rejected.
        - If any "allow" rule matches (and no deny matched), the request is accepted.
        - If no rules match at this priority level, move to the next group.

    If no rules match at any priority level, the request stays "pending".

    Args:
        request: The backend request to evaluate.

    Returns:
        The resulting status string: "accepted", "rejected", or "pending".
    """
    rules = Rule.objects.all().order_by("-priority")

    for _priority, group in groupby(rules, key=lambda rule: rule.priority):
        allow_matched = False
        deny_matched = False

        for rule in group:
            if not _matches(rule, request):
                continue

            if rule.action == RULE_ACTION_DENY:
                deny_matched = True
            elif rule.action == RULE_ACTION_ALLOW:
                allow_matched = True

        # P2: deny rules have priority over allow rules within the same priority level
        if deny_matched:
            return REQUEST_STATUS_REJECTED
        if allow_matched:
            return REQUEST_STATUS_ACCEPTED

    return REQUEST_STATUS_PENDING


def _matches(rule: Rule, request: BackendRequest) -> bool:
    """Dispatch matching logic based on the rule kind.

    Args:
        rule: The rule to evaluate.
        request: The backend request to evaluate against.

    Returns:
        True if the rule matches the request.
    """
    if rule.kind == RULE_KIND_HOSTNAME_AND_PATH_MATCH:
        return _hostname_and_path_match(rule, request)
    return False
