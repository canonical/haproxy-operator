# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Basic integration tests for the haproxy-route-policy charm."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_haproxy_route_policy_relation(
    application: str,
    juju: jubilant.Juju,
    any_charm_haproxy_route_policy_requirer: str,
    postgresql: str,
):
    """Test blocked->active transition after integrating with PostgreSQL.

    Args:
        application: The deployed haproxy-route-policy application name.
        juju: The Juju instance.

    Assert:
        The charm is blocked before relation and active after relating with PostgreSQL.
    """
    juju.integrate(f"{application}:database", f"{postgresql}:database")
    juju.integrate(
        f"{any_charm_haproxy_route_policy_requirer}:require-haproxy-route-policy",
        f"{application}:haproxy-route-policy",
    )
    juju.run(
        f"{any_charm_haproxy_route_policy_requirer}/0",
        action="rpc",
        params={"method": "update_relation"},
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, application, any_charm_haproxy_route_policy_requirer
        )
    )
    logger.info(juju.status().apps[application].relations["haproxy-route-policy"])
