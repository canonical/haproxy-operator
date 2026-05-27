# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator DNS record integration service."""

import logging

from charms.dns_record.v0.dns_record import (
    CreateRecordRequestError,
    DNSRecordRequires,
    RecordRequest,
)
from ops.model import Model

DNS_RECORD_RELATION = "dns-record"

logger = logging.getLogger(__name__)


class DNSRecordService:
    """Manages publishing DNS A records via the dns-record relation."""

    def __init__(self, model: Model, dns_record_requirer: DNSRecordRequires) -> None:
        """Initialise the service.

        Args:
            model: The charm's model.
            dns_record_requirer: The DNSRecordRequires library instance.
        """
        self.model = model
        self.dns_record_requirer = dns_record_requirer

    def update_dns_records(self, hostnames: list[str], ip: str) -> None:
        """Publish A records for all managed hostnames.

        Does nothing when there is no active dns-record relation, no hostnames,
        or no IP to publish.

        Args:
            hostnames: Hostnames to create A records for.
            ip: IPv4 address the records should resolve to.
        """
        if not hostnames or not ip:
            return

        relation = self.model.get_relation(self.dns_record_requirer.relation_name)
        if not relation:
            return

        entries: list[RecordRequest] = []
        for hostname in hostnames:
            try:
                entry = self.dns_record_requirer.create_record_request(
                    f"@ {hostname} 600 IN A {ip}"
                )
                entries.append(entry)
            except CreateRecordRequestError:
                logger.warning("Failed to create DNS record request for %s", hostname)

        if not entries:
            logger.info("No valid DNS record entries to publish, skipping update.")
            return

        self.dns_record_requirer.update_relation_data(entries)
