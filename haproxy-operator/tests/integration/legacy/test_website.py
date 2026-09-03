# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the website relation."""

import jubilant
import pytest
import requests

from .conftest import all_active_and_idle, get_unit_address


@pytest.mark.abort_on_fail
def test_website_relation(
    application: str,
    reverseproxy_requirer: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm.
    act: Add the website relation.
    assert: Requests to reverseproxy-requirer return the default haproxy page.
    """
    juju.integrate(f"{application}:website", f"{reverseproxy_requirer}:reverseproxy")
    juju.wait(
        lambda status: (
            any(
                relation.related_app == application
                for relation in status.apps[reverseproxy_requirer].relations.get(
                    "reverseproxy", []
                )
            )
            and all_active_and_idle(status, application, reverseproxy_requirer)
        ),
        delay=5,
        successes=6,
    )

    unit_address = get_unit_address(juju, reverseproxy_requirer)
    response = requests.get(unit_address, timeout=5)

    assert response.status_code == 200
    assert "Default page for the haproxy-operator charm" in str(response.content)
