# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy route policy."""

import logging


import jubilant
import pytest

logger = logging.getLogger(__name__)

TEST_HOSTNAME = "example.com"


@pytest.mark.abort_on_fail
def test_haproxy_route_policy(
    configured_application_with_tls: str,
    haproxy_route_policy: str,
    lxd_juju: jubilant.Juju,
    postgresql: str,
):
    """Test the HAProxy route policy integration."""
    lxd_juju.integrate(f"{haproxy_route_policy}:database", f"{postgresql}:database")
    lxd_juju.integrate(
        f"{configured_application_with_tls}:haproxy-route-policy",
        haproxy_route_policy,
    )
