# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pinned revisions of dependency charms used by the haproxy-route-policy-operator
integration tests.

Each constant is annotated with a structured comment that Renovate parses to look up
the latest matching revision on CharmHub for the given channel/base/arch combination and
open a PR when a newer one is available. See the "Dependency management on integration
tests" spec (ISD301) for the full standard.

The variable name MUST end with the suffix `_REVISION`.
"""

# NOTE: previously deployed without a pinned revision (implicitly tracked channel head).
# renovate: depName="postgresql" channel="16/edge" base="24.04" arch="amd64"
POSTGRESQL_REVISION = 1223
