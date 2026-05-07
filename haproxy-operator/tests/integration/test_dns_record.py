# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy-operator dns-record relation."""

import logging

import jubilant

logger = logging.getLogger(__name__)


def _dig(juju: jubilant.Juju, unit: str, nameserver: str, hostname: str) -> str:
    """Run a DNS query via dig from within a Juju unit.

    Args:
        juju: The jubilant Juju instance.
        unit: Unit to run dig from (e.g. 'haproxy/0').
        nameserver: IP address of the DNS server to query.
        hostname: Hostname to resolve.

    Returns:
        Raw dig output.
    """
    return juju.ssh(unit, f"dig +short @{nameserver} {hostname} A")


def test_dns_record_resolves_via_bind(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
):
    """
    arrange: haproxy and bind-operator integrated via dns-record, external-hostname set
    act: query bind's DNS server for the haproxy external hostname
    assert: bind resolves the hostname to haproxy's IP address
    """
    status = juju.status()
    bind_units = status.apps[bind_operator].units
    bind_ip = next(iter(bind_units.values())).address

    haproxy_units = status.apps[configured_application_with_tls].units
    haproxy_ip = next(iter(haproxy_units.values())).address

    dig_output = _dig(juju, f"{configured_application_with_tls}/0", bind_ip, "haproxy.internal")

    assert haproxy_ip in dig_output, (
        f"Expected bind to resolve 'haproxy.internal' to {haproxy_ip!r}, got: {dig_output!r}"
    )


def test_dns_record_updated_on_hostname_change(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
):
    """
    arrange: haproxy and bind-operator integrated
    act: change external-hostname config to a new hostname
    assert: bind resolves the new hostname to haproxy's IP
    """
    new_hostname = "haproxy-new.internal"
    juju.config(configured_application_with_tls, {"external-hostname": new_hostname})
    juju.wait(jubilant.all_active, timeout=5 * 60)

    status = juju.status()
    bind_units = status.apps[bind_operator].units
    bind_ip = next(iter(bind_units.values())).address

    haproxy_units = status.apps[configured_application_with_tls].units
    haproxy_ip = next(iter(haproxy_units.values())).address

    dig_output = _dig(juju, f"{configured_application_with_tls}/0", bind_ip, new_hostname)

    assert haproxy_ip in dig_output, (
        f"Expected bind to resolve {new_hostname!r} to {haproxy_ip!r}, got: {dig_output!r}"
    )

    juju.config(configured_application_with_tls, {"external-hostname": "haproxy.internal"})
    juju.wait(jubilant.all_active, timeout=5 * 60)


def test_dns_record_relation_removal_does_not_break_haproxy(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
):
    """
    arrange: haproxy and bind-operator integrated
    act: remove the dns-record relation
    assert: haproxy remains active with no error status
    """
    juju.cli(
        "remove-relation",
        f"{configured_application_with_tls}:dns-record",
        f"{bind_operator}:dns-record",
    )
    juju.wait(
        lambda status: status.apps[configured_application_with_tls].is_active,
        timeout=5 * 60,
    )
    juju.integrate(
        f"{configured_application_with_tls}:dns-record",
        f"{bind_operator}:dns-record",
    )
    juju.wait(jubilant.all_active, timeout=5 * 60)
