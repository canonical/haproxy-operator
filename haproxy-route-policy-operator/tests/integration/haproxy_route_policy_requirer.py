# pylint: disable=import-error
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import logging

# Ignoring here to make the linter happy as these modules will be available
# only inside the anycharm unit.
from any_charm_base import AnyCharmBase  # type: ignore
from haproxy_route_policy import (  # type: ignore
    HaproxyRoutePolicyBackendRequest,
    HaproxyRoutePolicyRequirer,
)

HAPROXY_ROUTE_POLICY_RELATION = "require-haproxy-route-policy"

logger = logging.getLogger()


class AnyCharm(AnyCharmBase):
    """haproxy-route requirer charm."""

    def __init__(self, *args, **kwargs):
        # We don't need to include *args and *kwargs in the docstring here.
        """Initialize the requirer charm."""
        super().__init__(*args, **kwargs)
        self._haproxy_route_policy = HaproxyRoutePolicyRequirer(
            self, HAPROXY_ROUTE_POLICY_RELATION
        )

    def update_relation(self):
        """Update haproxy-route-tcp relation data"""
        backend_requests = [
            HaproxyRoutePolicyBackendRequest(
                relation_id=1,
                port=4444,
                backend_name="test-backend",
                paths=["/"],
                hostname_acls=["example.com"],
            )
        ]
        self._haproxy_route_policy.provide_haproxy_route_policy_requests(backend_requests)
