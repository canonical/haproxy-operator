# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Basic integration tests for the haproxy-route-policy charm."""

import jubilant
import pytest


@pytest.mark.abort_on_fail
def test_charm_becomes_active_after_relation_with_postgresql(
    application: str, juju: jubilant.Juju
):
    """Test blocked->active transition after integrating with PostgreSQL.

    Args:
        application: The deployed haproxy-route-policy application name.
        juju: The Juju instance.

    Assert:
        The charm is blocked before relation and active after relating with PostgreSQL.
    """
    postgresql_app = "postgresql"
    juju.deploy(
        "postgresql", app=postgresql_app, channel="16/edge", base="ubuntu@24.04", log=False
    )

    juju.wait(lambda status: jubilant.all_blocked(status, application))

    juju.integrate(f"{application}:database", f"{postgresql_app}:database")
    juju.wait(lambda status: jubilant.all_active(status, application, postgresql_app))

    result = juju.run(f"{application}/0", "get-admin-credentials")
    assert result.results["username"] == "admin"
    # secrets.token_urlsafe(32) generates a string of length 43.
    assert len(result.results["password"]) == 43
