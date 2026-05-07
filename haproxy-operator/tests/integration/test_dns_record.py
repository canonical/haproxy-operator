# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy-operator dns-record relation."""

import json
import logging

import jubilant

logger = logging.getLogger(__name__)


def test_dns_record_relation_publishes_a_record(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
):
    """
    arrange: haproxy and bind-operator integrated via dns-record, external-hostname set
    act: wait for all charms to be active
    assert: haproxy's dns-record relation databag contains an A record for the external hostname
    """
    relations_output = juju.cli(
        "show-unit",
        f"{configured_application_with_tls}/0",
        "--format=json",
    )
    unit_data = json.loads(relations_output)

    dns_relation_data = None
    for unit_info in unit_data.values():
        for relation in unit_info.get("relation-info", []):
            if relation.get("endpoint") == "dns-record":
                dns_relation_data = relation
                break

    assert dns_relation_data is not None, "dns-record relation not found in unit data"

    app_data_raw = dns_relation_data.get("application-data", {})
    dns_entries_raw = app_data_raw.get("dns_entries")
    assert dns_entries_raw is not None, "dns_entries key missing from relation databag"

    dns_entries = json.loads(dns_entries_raw)
    assert len(dns_entries) >= 1, "Expected at least one DNS entry in the databag"

    domains = [entry.get("domain") for entry in dns_entries]
    assert "haproxy.internal" in domains, (
        f"Expected 'haproxy.internal' in DNS entries, got: {domains}"
    )
    record_types = [entry.get("record_type") for entry in dns_entries]
    assert "A" in record_types, f"Expected an A record, got record types: {record_types}"


def test_dns_record_updated_on_hostname_change(
    juju: jubilant.Juju,
    configured_application_with_tls: str,
    bind_operator: str,
):
    """
    arrange: haproxy and bind-operator integrated, new hostname configured
    act: change external-hostname config
    assert: the new hostname appears in the dns-record databag
    """
    new_hostname = "haproxy-new.internal"
    juju.config(configured_application_with_tls, {"external-hostname": new_hostname})
    juju.wait(jubilant.all_active, timeout=5 * 60)

    relations_output = juju.cli(
        "show-unit",
        f"{configured_application_with_tls}/0",
        "--format=json",
    )
    unit_data = json.loads(relations_output)

    dns_relation_data = None
    for unit_info in unit_data.values():
        for relation in unit_info.get("relation-info", []):
            if relation.get("endpoint") == "dns-record":
                dns_relation_data = relation
                break

    assert dns_relation_data is not None
    app_data_raw = dns_relation_data.get("application-data", {})
    dns_entries = json.loads(app_data_raw.get("dns_entries", "[]"))
    domains = [entry.get("domain") for entry in dns_entries]
    assert new_hostname in domains, f"New hostname {new_hostname!r} not found in: {domains}"

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
