# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
# Since the relations invoked in the methods are taken from the charm,
# mypy guesses the relations might be None about all of them.
"""Haproxy TLS relation business logic."""

import logging
import typing
from pathlib import Path

from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    PrivateKey,
    ProviderCertificate,
    TLSCertificatesRequiresV4,
)
from ops.model import Model

from haproxy import file_exists, read_file, render_file

TLS_CERT = "certificates"
HAPROXY_CERTS_DIR = Path("/var/lib/haproxy/certs")

logger = logging.getLogger()


class TLSRelationService:
    """TLS Relation service class."""

    def __init__(self, model: Model, certificates: TLSCertificatesRequiresV4) -> None:
        """Init method for the class.

        Args:
            model: The charm's current model.
            certificates: The TLS certificates requirer library.
        """
        self.certificates = certificates
        self.model = model
        self.application = self.model.app
        self.integration_name = self.certificates.relationship_name

    def get_provider_cert_with_hostname(
        self, hostname: str
    ) -> typing.Optional[ProviderCertificate]:
        """Get a cert from the provider's integration data that matches 'certificate'.

        Args:
            hostname: the hostname to match with provider certificates

        Returns:
            typing.Optional[ProviderCertificate]: ProviderCertificate if exists, else None.
        """
        if len(self.certificates.certificate_requests) == 0:
            return None
        provider_certificate, _ = self.certificates.get_assigned_certificate(
            certificate_request=self.certificates.certificate_requests[0]
        )
        if not provider_certificate:
            return None
        if not provider_certificate.certificate:
            return None
        if provider_certificate.certificate.common_name != hostname:
            return None
        return provider_certificate

    def certificate_available(self) -> None:
        """Handle TLS Certificate available event."""
        if len(self.certificates.certificate_requests) == 0:
            logger.warning("No certificate was requested")
            return
        provider_certificate, private_key = self.certificates.get_assigned_certificate(
            certificate_request=self.certificates.certificate_requests[0]
        )
        if not provider_certificate:
            logger.warning("Provider certificate is not available")
            return
        if not private_key:
            logger.warning("Private key is not available")
            return
        if not self._certificate_matches_stored_content(
            certificate=provider_certificate.certificate,
            private_key=private_key,
        ):
            self.write_certificate_to_unit(
                certificate=provider_certificate.certificate,
                private_key=private_key,
            )

    def _certificate_matches_stored_content(
        self, certificate: Certificate, private_key: PrivateKey
    ) -> bool:
        """Check if the certificate matches the stored content.

        Args:
            certificate: The certificate to check.
            private_key: The private key to check.
        """
        if not file_exists(HAPROXY_CERTS_DIR / f"{certificate.common_name}.pem"):
            return False
        expected_certificate = f"{str(certificate)}\n{str(private_key)}"
        existing_certificate = read_file(HAPROXY_CERTS_DIR / f"{certificate.common_name}.pem")
        return expected_certificate == existing_certificate

    def write_certificate_to_unit(self, certificate: Certificate, private_key: PrivateKey) -> None:
        """Store certificate in workload.

        Args:
            certificate: The certificate to store.
            private_key: The private key to store.
        """
        if not HAPROXY_CERTS_DIR.exists(follow_symlinks=False):
            HAPROXY_CERTS_DIR.mkdir(exist_ok=True)
        hostname = certificate.common_name
        pem_file_path = Path(HAPROXY_CERTS_DIR / f"{hostname}.pem")
        pem_file_content = f"{str(certificate)}\n{str(private_key)}"
        render_file(pem_file_path, pem_file_content, 0o644)
        logger.info("Certificate pem file written: %r", pem_file_path)
