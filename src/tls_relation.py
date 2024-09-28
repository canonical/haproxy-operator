# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
# Since the relations invoked in the methods are taken from the charm,
# mypy guesses the relations might be None about all of them.
"""Haproxy TLS relation business logic."""
import logging
import secrets
import string
import typing
from pathlib import Path

from charms.tls_certificates_interface.v3.tls_certificates import (
    ProviderCertificate,
    TLSCertificatesRequiresV3,
    generate_csr,
    generate_private_key,
)
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtensionOID, NameOID
from ops.model import Model, Relation, SecretNotFoundError

from haproxy import render_file

TLS_CERT = "certificates"
HAPROXY_CERTS_DIR = Path("/var/lib/haproxy/certs")

logger = logging.getLogger()


class InvalidCertificateError(Exception):
    """Exception raised when certificates is invalid."""


class GetPrivateKeyError(Exception):
    """Exception raised when the private key secret doesn't exist."""


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
    subject_alternative_name = decoded_cert.subject.get_attributes_for_oid(
        ExtensionOID.SUBJECT_ALTERNATIVE_NAME
    )
    common_name_and_sans = common_name_attribute + subject_alternative_name

    if not common_name_and_sans:
        raise InvalidCertificateError(
            f"Cannot parse hostname from x509 certificate: {certificate}"
        )

    return str(common_name_and_sans[0].value)


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
        """
        # At this point, TLSInformation state component should already be initialized
        tls_integration = self.model.get_relation(self.integration_name)
        assert tls_integration  # nosec: B101

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
        """Return the private key and its password from juju secrets.

        Args:
            hostname: The hostname of the private key we want to fetch.

        Returns:
            The encrypted private key.

        Raises:
            GetPrivateKeyError: When failed getting the required private key.
        """
        try:
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            private_key = secret.get_content()["key"]
            password = secret.get_content()["password"]
        except SecretNotFoundError as exc:
            logger.exception("Private key for hostname: %s not found", hostname)
            raise GetPrivateKeyError(f"Private key for hostname: {hostname} not found") from exc
        return KeyPair(private_key, password)

    def get_provider_cert_with_hostname(
        self, hostname: str
    ) -> typing.Optional[ProviderCertificate]:
        """Get a cert from the provider's integration data that matches 'certificate'.

        Args:
            hostname: the hostname to match with provider certificates

        Returns:
            typing.Optional[ProviderCertificate]: ProviderCertificate if exists, else None.
        """
        for cert in self.certificates.get_provider_certificates():
            if get_hostname_from_cert(cert.certificate) == hostname:
                return cert
        return None

    def certificate_expiring(self, certificate: str) -> None:
        """Handle the TLS Certificate expiring event.

        Generate a new CSR and request for a new certificate.

        Args:
            certificate: The invalidated certificate.
        """
        if expiring_cert := self._get_cert(certificate):
            hostname = get_hostname_from_cert(expiring_cert.certificate)
            old_csr = expiring_cert.csr
            private_key, password = self._get_private_key(hostname)
            new_csr = generate_csr(
                private_key=private_key.encode(),
                private_key_password=password.encode(),
                subject=hostname,
                sans_dns=[hostname],
            )
            self.certificates.request_certificate_renewal(
                old_certificate_signing_request=old_csr.encode(),
                new_certificate_signing_request=new_csr,
            )

    def certificate_invalidated(
        self,
        certificate: typing.Optional[str] = None,
        provider_certificate: typing.Optional[ProviderCertificate] = None,
    ) -> None:
        """Handle TLS Certificate revocation.

        Args:
            certificate: The invalidated certificate to match with a provider certificate.
            provider_certificate: The provider certificate, skip certificate matching
            if this is provided directly.
        """
        if not certificate and not provider_certificate:
            return

        invalidated_provider_certificate = provider_certificate
        if provider_certificate is None:
            # certificate should always be set here
            matched_provider_certificate = self._get_cert(typing.cast(str, certificate))
            if not matched_provider_certificate:
                logger.error("Cannot find provider certificate with provided certificate string.")
                return
            invalidated_provider_certificate = matched_provider_certificate

        # invalidated_provider_certificate should always be set here
        invalidated_provider_certificate = typing.cast(
            ProviderCertificate, invalidated_provider_certificate
        )
        try:
            hostname = get_hostname_from_cert(invalidated_provider_certificate.certificate)
            self.remove_certificate_from_unit(hostname)
            secret = self.model.get_secret(label=f"private-key-{hostname}")
            secret.remove_all_revisions()
        except SecretNotFoundError:
            logger.exception("Secret not found, skipping deletion")

    def certificate_available(
        self,
        certificate: str,
    ) -> None:
        """Handle TLS Certificate available event.

        Args:
            certificate: The provided certificate.
        """
        self.write_certificate_to_unit(certificate)

    def all_certificate_invalidated(self) -> None:
        """Clean up certificates in unit and private key secrets."""
        for cert in self.certificates.get_provider_certificates():
            self.certificate_invalidated(provider_certificate=cert)

    def write_certificate_to_unit(self, certificate: str) -> None:
        """Write the certificate having "hostname" to haproxy cert directory.

        Args:
            certificate: the certificate to write to the unit filesystem.
        """
        if not HAPROXY_CERTS_DIR.exists(follow_symlinks=False):
            HAPROXY_CERTS_DIR.mkdir(exist_ok=True)

        hostname = get_hostname_from_cert(certificate)
        key_pair = self._get_private_key(hostname)
        decrypted_private_key = _get_decrypted_key(key_pair.private_key, key_pair.password)
        pem_file_content = f"{certificate}\n{decrypted_private_key}"
        pem_file_path = Path(HAPROXY_CERTS_DIR / f"{hostname}.pem")
        render_file(pem_file_path, pem_file_content, 0o644)

    def remove_certificate_from_unit(self, hostname: str) -> None:
        """Remove the certificate having "hostname" from haproxy cert directory.

        Args:
            hostname: the hostname of the provider certificate.
        """
        pem_file_path = Path(HAPROXY_CERTS_DIR / f"{hostname}.pem")
        logger.info("Removing certificate pem file: %r", pem_file_path)
        pem_file_path.unlink(missing_ok=True)

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


def _get_decrypted_key(private_key: str, password: str) -> str:
    """Decrypted the provided private key using the provided password.

    Args:
        private_key: The encrypted private key.
        password: The password to decrypt the private key.

    Returns:
        The decrypted private key.
    """
    decrypted_key = serialization.load_pem_private_key(
        private_key.encode(), password=password.encode()
    )

    return decrypted_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
