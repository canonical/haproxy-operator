# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import jubilant
import requests

from .conftest import get_unit_ip_address


def test_ha(application: str, hacluster: str, juju: jubilant.Juju):
    """
    arrange: deploy the haproxy charm.
    act: integrate hacluster and configure vip.
    assert: confirm that the charm is active after HA integration.
    """
    juju.config(hacluster, {"cluster_count": "1", "no_quorum_policy": "ignore"})
    juju.wait(lambda status: jubilant.all_active(status, application))

    juju.integrate(f"{application}:ha", f"{hacluster}:ha")
    # We wait up to 10 minutes to ensure hacluster has enough time to go into idle state.
    juju.wait(lambda status: status.apps[application].is_blocked, timeout=10 * 60)

    vip = get_unit_ip_address(juju, application)
    juju.config(application, {"vip": str(vip)})
    juju.wait(lambda status: jubilant.all_active(status, application, hacluster))

    response = requests.get(url=f"http://{vip}", timeout=30)
    assert "Default page for the haproxy-operator charm" in response.text
