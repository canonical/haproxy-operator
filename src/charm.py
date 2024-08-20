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
)
from ops.charm import ActionEvent

import haproxy
from http_interface import HTTPDataProvidedEvent, HTTPProvider
from state.config import CharmConfig
from state.tls import TLSInformation
from state.validation import validate_config_and_integration
from tls_relation import TLSRelationService

logger = logging.getLogger(__name__)

TLS_CERT_RELATION = "certificates"
REVERSE_PROXY_INTEGRATION = "reverseproxy"


class HAProxyCharm(ops.CharmBase):
    """Charm haproxy."""

    def __init__(self, *args: typing.Any):
        """Initialize the charm and register event handlers.

        Args:
            args: Arguments to initialize the charm base.
        """
        super().__init__(*args)
        self.haproxy_service = haproxy.HAProxyService()

        self.certificates = TLSCertificatesRequiresV3(self, TLS_CERT_RELATION)
        self._tls = TLSRelationService(self.model, self.certificates)

        self.http_provider = HTTPProvider(self, REVERSE_PROXY_INTEGRATION)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.get_certificate_action, self._on_get_certificate_action)
        self.framework.observe(
            self.http_provider.on.data_provided, self._on_reverse_proxy_data_provided
        )

    def _on_install(self, _: typing.Any) -> None:
        """Install the haproxy package."""
        self.haproxy_service.install()
        self.unit.status = ops.ActiveStatus()

    def _on_config_changed(self, _: typing.Any) -> None:
        """Handle the config-changed event."""
        self._reconcile_certificates()
        self._reconcile()

    @validate_config_and_integration(defer=False)
    def _on_certificate_available(self, _: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event."""
        self._reconcile()

    @validate_config_and_integration(defer=False)
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

    def _on_reverse_proxy_data_provided(self, event: HTTPDataProvidedEvent) -> None:
        """Handle data_provided event for reverseproxy integration.

        Args:
            event: data-provided event.
        """
        for unit in event.hosts:
            logger.info(
                "reverseproxy integration data provided for unit: %s %s", unit.hostname, unit.port
            )

    @validate_config_and_integration(defer=False)
    def _reconcile(self) -> None:
        """Render the haproxy config and restart the service."""
        config = CharmConfig.from_charm(self)
        self.haproxy_service.render_haproxy_config(config)

    @validate_config_and_integration(defer=False)
    def _reconcile_certificates(self) -> None:
        """Request new certificates if needed to match the configured hostname."""
        tls_information = TLSInformation.from_charm(self, self.certificates)
        if not self._tls.get_provider_cert_with_hostname(tls_information.external_hostname):
            self._tls.generate_private_key(tls_information.external_hostname)
            self._tls.request_certificate(tls_information.external_hostname)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(HAProxyCharm)
