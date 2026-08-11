# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""

import jubilant


def test_config(application: str, juju: jubilant.Juju):
    """
    arrange: Deploy the charm.
    act: Update the charm config to an invalid value and then a valid value.
    assert: The charm correctly blocks the first time and writes the configured
    value to haproxy.cfg the second time.
    """
    juju.config(application, {"global-maxconn": "-1"})
    juju.wait(lambda status: status.apps[application].is_blocked)

    juju.config(application, {"global-maxconn": "1024"})
    juju.wait(lambda status: jubilant.all_active(status, application))

    stdout = juju.ssh(f"{application}/0", "cat /etc/haproxy/haproxy.cfg")
    assert "maxconn 1024" in stdout
