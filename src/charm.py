#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""haproxy-operator charm file."""

import logging
import typing

import ops
from charms.tls_certificates_interface.v3.tls_certificates import (
    CertificateAvailableEvent,
    TLSCertificatesRequiresV3,
    CertificateExpiringEvent,
    CertificateInvalidatedEvent,
)
from charms.traefik_k8s.v2.ingress import (
    IngressPerAppDataProvidedEvent,
    IngressPerAppDataRemovedEvent,
    IngressPerAppProvider,
)
from ops.charm import ActionEvent

from haproxy import HAProxyService
from http_interface import HTTPDataProvidedEvent, HTTPDataRemovedEvent, HTTPProvider
from state.config import CharmConfig
from state.ingress import IngressRequirersInformation
from state.tls import TLSInformation
from state.validation import validate_config_and_integration
from tls_relation import TLSRelationService, get_hostname_from_cert

logger = logging.getLogger(__name__)

INGRESS_RELATION = "ingress"
TLS_CERT_RELATION = "certificates"
REVERSE_PROXY_RELATION = "reverseproxy"


class HAProxyCharm(ops.CharmBase):
    """Charm haproxy.

    Attrs:
        bind_address: The IP address of each haproxy unit.
    """

    def __init__(self, *args: typing.Any):
        """Initialize the charm and register event handlers.

        Args:
            args: Arguments to initialize the charm base.
        """
        super().__init__(*args)
        self.haproxy_service = HAProxyService()
        self.certificates = TLSCertificatesRequiresV3(self, TLS_CERT_RELATION)
        self._tls = TLSRelationService(self.model, self.certificates)
        self._ingress_provider = IngressPerAppProvider(charm=self, relation_name=INGRESS_RELATION)
        self.http_provider = HTTPProvider(self, REVERSE_PROXY_RELATION)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(
            self.certificates.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.certificates.on.certificate_expiring, self._on_certificate_expiring
        )
        self.framework.observe(
            self.certificates.on.certificate_invalidated, self._on_certificate_invalidated
        )
        self.framework.observe(self.on.get_certificate_action, self._on_get_certificate_action)
        self.framework.observe(
            self.http_provider.on.data_provided, self._on_reverse_proxy_data_provided
        )
        self.framework.observe(
            self.http_provider.on.data_provided, self._on_reverse_proxy_data_removed
        )
        self.framework.observe(
            self._ingress_provider.on.data_provided, self._on_ingress_data_provided
        )
        self.framework.observe(
            self._ingress_provider.on.data_removed, self._on_ingress_data_removed
        )

    @property
    def bind_address(self) -> typing.Union[str, None]:
        """Get Unit bind address.

        Returns:
            str: A single address that the charm's application should bind() to.
        """
        if bind := self.model.get_binding("juju-info"):
            return str(bind.network.bind_address)
        return None

    def _on_install(self, _: typing.Any) -> None:
        """Install the haproxy package."""
        self.haproxy_service.install()

    def _on_config_changed(self, _: typing.Any) -> None:
        """Handle the config-changed event."""
        self._reconcile_certificates()
        self._reconcile()

    def _on_certificate_available(self, event: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event.

        Args:
            event: Juju event
        """
        hostname = get_hostname_from_cert(event.certificate)
        self._tls.write_certificate_to_unit(hostname)
        self._reconcile()

    def _on_certificate_expiring(self, event: CertificateExpiringEvent) -> None:
        """Handle the TLS Certificate expiring event.

        Args:
            event: The event that fires this method.
        """
        TLSInformation.validate_certificates_integration(self)
        self._tls.certificate_expiring(event)

    def _on_certificate_invalidated(self, event: CertificateInvalidatedEvent) -> None:
        """Handle the TLS Certificate invalidation event.

        Args:
            event: The event that fires this method.
        """
        TLSInformation.validate_certificates_integration(self)
        if event.reason == "revoked":
            self._tls.certificate_invalidated(event)
        if event.reason == "expired":
            self._tls.certificate_expiring(event)
        self.unit.status = ops.MaintenanceStatus("Waiting for new certificate")

    def _on_get_certificate_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-certificate` Juju action.

        Args:
            event: Juju event
        """
        TLSInformation.validate_certificates_integration(self)

        hostname = event.params["hostname"]
        if provider_cert := self._tls.get_provider_cert_with_hostname(hostname):
            event.set_results(
                {
                    "certificate": provider_cert.certificate,
                    "ca": provider_cert.ca,
                    "chain": provider_cert.chain_as_pem(),
                }
            )
            return

        event.fail(f"Missing or incomplete certificate data for {hostname}")

    def _on_reverse_proxy_data_provided(self, _: HTTPDataProvidedEvent) -> None:
        """Handle data_provided event for reverseproxy integration."""
        self._reconcile()

    def _on_reverse_proxy_data_removed(self, _: HTTPDataRemovedEvent) -> None:
        """Handle data_removed event for reverseproxy integration."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _reconcile(self) -> None:
        """Render the haproxy config and restart the service."""
        config = CharmConfig.from_charm(self)
        services_dict = self.http_provider.get_services_definition()
        ingress_requirers_information = IngressRequirersInformation.from_provider(
            self._ingress_provider
        )
        self.haproxy_service.reconcile(config, services_dict, ingress_requirers_information)
        logger.info("Setting active status")
        self.unit.status = ops.ActiveStatus()

    @validate_config_and_integration(defer=False)
    def _reconcile_certificates(self) -> None:
        """Request new certificates if needed to match the configured hostname."""
        tls_information = TLSInformation.from_charm(self, self.certificates)
        if not self._tls.get_provider_cert_with_hostname(tls_information.external_hostname):
            self._tls.generate_private_key(tls_information.external_hostname)
            self._tls.request_certificate(tls_information.external_hostname)

    def _on_ingress_data_provided(self, event: IngressPerAppDataProvidedEvent) -> None:
        """Handle the data-provided event.

        Args:
            event: Juju event.
        """
        self._reconcile()
        integration_data = self._ingress_provider.get_data(event.relation)
        path_prefix = f"{integration_data.app.model}-{integration_data.app.name}"
        self._ingress_provider.publish_url(
            event.relation, f"http://{self.bind_address}/{path_prefix}/"
        )

    def _on_ingress_data_removed(self, _: IngressPerAppDataRemovedEvent) -> None:
        """Handle the data-removed event."""
        self._reconcile()


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(HAProxyCharm)
