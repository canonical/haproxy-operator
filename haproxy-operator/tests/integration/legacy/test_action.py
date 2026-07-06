# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for actions."""

import jubilant
import pytest

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


@pytest.mark.abort_on_fail
def test_get_certificate_action(
    configured_application_with_tls: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm with valid config and tls integration.
    act: Run the get-certificate action and run a sh command to check
    the cert location on the unit.
    assert: The output of both operations are valid.
    """
    task = juju.run(
        f"{configured_application_with_tls}/0",
        "get-certificate",
        {"hostname": TEST_EXTERNAL_HOSTNAME_CONFIG},
    )
    assert "-----BEGIN CERTIFICATE-----" in task.results.get("certificate", "")

    stdout = juju.ssh(f"{configured_application_with_tls}/0", "ls /var/lib/haproxy/certs")
    assert f"{TEST_EXTERNAL_HOSTNAME_CONFIG}.pem" in stdout

    # The action should fail when run without the required hostname parameter.
    # disable ruff B017 error (assert-raises-exception) for using Exception in pytest.raises
    with pytest.raises(Exception):  # noqa: B017
        juju.run(f"{configured_application_with_tls}/0", "get-certificate")
