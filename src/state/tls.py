# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm tls information."""

import logging
import re
import typing
from dataclasses import dataclass

import ops
from charms.tls_certificates_interface.v4.tls_certificates import TLSCertificatesRequiresV4

TLS_CERTIFICATES_INTEGRATION = "certificates"
HOSTNAME_REGEX = r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"

logger = logging.getLogger()


class TLSNotReadyError(Exception):
    """Exception raised when the charm is not ready to handle TLS."""


@dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing information about TLS.

    Attributes:
        external_hostname: Configured external hostname.
        tls_certs: A dict of hostname: certificate obtained from the relation.
    """

    external_hostname: str
    tls_certs: dict[str, str]

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, certificates: TLSCertificatesRequiresV4
    ) -> "TLSInformation":
        """Get TLS information from a charm instance.

        Args:
            charm: The haproxy charm.
            certificates: TLS certificates requirer library.

        Returns:
            TLSInformation: Information about configured TLS certs.
        """
        cls.validate(charm)

        external_hostname = typing.cast(str, charm.config.get("external-hostname"))
        tls_certs = {}

        provider_certificates, _ = certificates.get_assigned_certificates()
        for provider_certificate in provider_certificates:
            hostname = provider_certificate.certificate.common_name
            tls_certs[hostname] = provider_certificate.certificate

        return cls(
            external_hostname=external_hostname,
            tls_certs=tls_certs,
        )

    @classmethod
    def validate(cls, charm: ops.CharmBase) -> None:
        """Validate the precondition to initialize this state component.

        Args:
            charm: The haproxy charm.

        Raises:
            TLSNotReadyError: if the charm is not ready to handle TLS.
        """
        tls_requirer_integration = charm.model.get_relation(TLS_CERTIFICATES_INTEGRATION)
        external_hostname = typing.cast(str, charm.config.get("external-hostname", ""))

        if not re.match(HOSTNAME_REGEX, external_hostname):
            logger.error(
                "Configured hostname (%s) does not match regex: %s",
                external_hostname,
                HOSTNAME_REGEX,
            )
            raise TLSNotReadyError("Invalid hostname configuration.")

        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            logger.error("Relation or relation data not ready.")
            raise TLSNotReadyError("Certificates relation or relation data not ready.")
