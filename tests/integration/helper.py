# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Helper methods for integration tests."""

import ipaddress
import subprocess  # nosec
from contextlib import contextmanager

import jubilant


def get_unit_ip_address(
    juju: jubilant.Juju,
    application: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Get the unit IP address of a Juju application to make HTTP requests.

    Args:
        juju: Jubilant Juju instance.
        application: The name of the deployed application.

    Returns:
        The IP address of the first unit.
    """
    status = juju.status()
    app_status = status.apps.get(application)
    assert app_status, f"Application {application} not found in model status"
    unit_status = next(iter(app_status.units.values()))
    address = unit_status.public_address
    assert address, f"Unit of {application} has no public address"
    return ipaddress.ip_address(address)


def get_unit_address(juju: jubilant.Juju, application: str) -> str:
    """Get the HTTP address of the first unit of a Juju application.

    Args:
        juju: Jubilant Juju instance.
        application: The name of the deployed application.

    Returns:
        A string representing the base HTTP URL for the first unit.
    """
    unit_ip_address = get_unit_ip_address(juju, application)
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        return f"http://[{unit_ip_address}]"
    return f"http://{unit_ip_address}"


@contextmanager
def patch_etc_hosts(ip, hostname):
    # I could not come with a better idea...
    etc_host_line = f"{ip} {hostname} #test"
    command_add_line = f"/bin/echo '{etc_host_line}' | sudo tee -a /etc/hosts"
    subprocess.run(command_add_line, shell=True)  # nosec
    try:
        yield
    finally:
        command_remove_line = f"sudo sed -i '/^{etc_host_line}$/d' /etc/hosts"
        subprocess.run(command_remove_line, shell=True)  # nosec
