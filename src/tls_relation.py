# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
# Since the relations invoked in the methods are taken from the charm,
# mypy guesses the relations might be None about all of them.
"""Gateway API TLS relation business logic."""
import logging
import secrets
import string
import typing

from charms.tls_certificates_interface.v3.tls_certificates import (
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
    ProviderCertificate,
    TLSCertificatesRequiresV3,
    generate_csr,
    generate_private_key,
)
from cryptography import x509
from cryptography.x509.oid import NameOID
from ops.model import Model, Relation, SecretNotFoundError

TLS_CERT = "certificates"
logger = logging.getLogger()


class InvalidCertificateError(Exception):
    """Exception raised when certificates is invalid."""


class KeyPair(typing.NamedTuple):
    """Stores a private key and encryption password.

    Attributes:
        private_key: The private key
        password: The password used for encryption
    """

    private_key: str
    password: str


def get_hostname_from_cert(certificate: str) -> str:
    """Get the hostname from a certificate subject name.

    Args:
        certificate: The certificate in PEM format.

    Returns:
        The hostname the certificate is issue to.

    Raises:
        InvalidCertificateError: When hostname cannot be parsed from the given certificate.
    """
    decoded_cert = x509.load_pem_x509_certificate(certificate.encode())

    common_name_attribute = decoded_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if not common_name_attribute:
        raise InvalidCertificateError(
            f"Cannot parse hostname from x509 certificate: {certificate}"
        )

    return str(common_name_attribute[0].value)


class TLSRelationService:
    """TLS Relation service class."""

    def __init__(self, model: Model, certificates: TLSCertificatesRequiresV3) -> None:
        """Init method for the class.

        Args:
            model: The charm's current model.
            certificates: The TLS certificates requirer library.
        """
        self.certificates = certificates
        self.model = model
        self.application = self.model.app
        self.integration_name = self.certificates.relationship_name

    def generate_password(self) -> str:
        """Generate a random 12 character password.

        Returns:
            str: Private key string.
        """
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(12))

    def request_certificate(self, hostname: str) -> None:
        """Handle the TLS Certificate joined event.

        Args:
            hostname: Certificate's hostname.
        """
        private_key, password = self._get_private_key(hostname)
        csr = generate_csr(
            private_key=private_key.encode(),
            private_key_password=password.encode(),
            subject=hostname,
            sans_dns=[hostname],
        )
        self.certificates.request_certificate_creation(certificate_signing_request=csr)

    def generate_private_key(self, hostname: str) -> None:
        """Handle the TLS Certificate created event.

        Args:
            hostname: Certificate's hostname.

        Raises:
            AssertionError: If this method is called before the certificates integration is ready.
        """
        # At this point, TLSInformation state component should already be initialized
        tls_integration = self.model.get_relation(self.integration_name)
        if not tls_integration:
            raise AssertionError

        tls_integration = typing.cast(Relation, tls_integration)

        private_key_password = self.generate_password().encode()
        private_key = generate_private_key(password=private_key_password)
        private_key_dict = {
            "password": private_key_password.decode(),
            "key": private_key.decode(),
        }
        try:
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            secret.set_content(private_key_dict)
        except SecretNotFoundError:
            secret = self.application.add_secret(
                content=private_key_dict, label=f"private-key-{hostname}"
            )
            secret.grant(tls_integration)

    def _get_private_key(self, hostname: str) -> KeyPair:
        """Return the private key and its password from either juju secrets or the relation data.

        Args:
            hostname: The hostname of the private key we want to fetch.

        Returns:
            The encrypted private key.
        """
        secret = self.model.get_secret(label=f"private-key-{hostname}")
        private_key = secret.get_content()["key"]
        password = secret.get_content()["password"]
        return KeyPair(private_key, password)

    def _get_cert(self, certificate: str) -> typing.Optional[ProviderCertificate]:
        """Get a cert from the provider's integration data that matches 'certificate'.

        Args:
            certificate: the certificate to match with provider certificates

        Returns:
            typing.Optional[ProviderCertificate]: ProviderCertificate if exists, else None.
        """
        provider_certificates = self.certificates.get_provider_certificates()
        matching_certs = [
            cert for cert in provider_certificates if cert.certificate == certificate
        ]
        return matching_certs[0] if matching_certs else None
