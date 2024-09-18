# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-operator charm tls information."""

import logging
import re
import typing
from dataclasses import dataclass

import ops
from charms.tls_certificates_interface.v3.tls_certificates import TLSCertificatesRequiresV3

from tls_relation import get_hostname_from_cert

from .exception import CharmStateValidationBaseError

TLS_CERTIFICATES_INTEGRATION = "certificates"
HOSTNAME_REGEX = r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*"
HAPROXY_CRT_DIR = "/var/lib/haproxy/certs/"

logger = logging.getLogger()


class TLSNotReadyError(CharmStateValidationBaseError):
    """Exception raised when the charm is not ready to handle TLS."""


@dataclass(frozen=True)
class TLSInformation:
    """A component of charm state containing information about TLS.

    Attributes:
        external_hostname: Configured external hostname.
        tls_certs: A dict of hostname: certificate obtained from the relation.
        tls_keys: A dict of hostname: private_key stored in juju secrets.
    """

    external_hostname: str
    tls_certs: dict[str, str]
    tls_keys: dict[str, dict[str, str]]

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, certificates: TLSCertificatesRequiresV3
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
        tls_keys = {}

        for cert in certificates.get_provider_certificates():
            hostname = get_hostname_from_cert(cert.certificate)
            tls_certs[hostname] = cert.certificate
            secret = charm.model.get_secret(label=f"private-key-{hostname}")
            tls_keys[hostname] = {
                "key": secret.get_content()["key"],
                "password": secret.get_content()["password"],
            }

        return cls(
            external_hostname=external_hostname,
            tls_certs=tls_certs,
            tls_keys=tls_keys,
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
            logger.error("Configured hostname does not match regex: %s", HOSTNAME_REGEX)
            raise TLSNotReadyError("Invalid hostname configuration.")

        if (
            tls_requirer_integration is None
            or tls_requirer_integration.data.get(charm.app) is None
        ):
            logger.error("Relation or relation data not ready.")
            raise TLSNotReadyError("Certificates relation or relation data not ready.")
