#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""haproxy-operator charm file."""

import logging
import typing

import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider
from charms.haproxy.v1.haproxy_route import HaproxyRouteProvider
from charms.tls_certificates_interface.v4.tls_certificates import (
    CertificateAvailableEvent,
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)
from charms.traefik_k8s.v1.ingress_per_unit import (
    IngressDataReadyEvent,
    IngressDataRemovedEvent,
    IngressPerUnitProvider,
)
from charms.traefik_k8s.v2.ingress import (
    IngressPerAppDataProvidedEvent,
    IngressPerAppDataRemovedEvent,
    IngressPerAppProvider,
)
from interface_hacluster.ops_ha_interface import HAServiceRequires
from ops.charm import ActionEvent
from ops.model import Port

from haproxy import HAPROXY_SERVICE, HAProxyService
from http_interface import (
    HTTPBackendAvailableEvent,
    HTTPBackendRemovedEvent,
    HTTPProvider,
    HTTPRequirer,
)
from state.charm_state import CharmState, ProxyMode
from state.exception import CharmStateValidationBaseError
from state.ha import HACLUSTER_INTEGRATION, HAPROXY_PEER_INTEGRATION, HAInformation
from state.haproxy_route import (
    HAPROXY_ROUTE_RELATION,
    HaproxyRouteIntegrationDataValidationError,
    HaproxyRouteRequirersInformation,
)
from state.ingress import IngressRequirersInformation
from state.ingress_per_unit import IngressPerUnitRequirersInformation
from state.tls import TLSInformation, TLSNotReadyError
from state.validation import validate_config_and_tls
from tls_relation import TLSRelationService

logger = logging.getLogger(__name__)

INGRESS_RELATION = "ingress"
TLS_CERT_RELATION = "certificates"
REVERSE_PROXY_RELATION = "reverseproxy"
WEBSITE_RELATION = "website"


class HaproxyUnitAddressNotAvailableError(CharmStateValidationBaseError):
    """Exception raised when ingress integration is not established."""


class ReverseProxyInvalidPortError(CharmStateValidationBaseError):
    """Exception raised when a requested port is not a valid TCP port."""


def _validate_port(port: int) -> bool:
    """Validate if the given value is a valid TCP port.

    Args:
        port: The port number to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    return 0 <= port <= 65535


# pylint: disable=too-many-instance-attributes
class HAProxyCharm(ops.CharmBase):
    """Charm haproxy."""

    def __init__(self, *args: typing.Any):
        """Initialize the charm and register event handlers.

        Args:
            args: Arguments to initialize the charm base.
        """
        super().__init__(*args)
        self.haproxy_service = HAProxyService()
        # Order is important here as we want _ensure_tls to check if the hostname is configured
        self.framework.observe(self.on[TLS_CERT_RELATION].relation_created, self._ensure_tls)
        self.framework.observe(self.on[TLS_CERT_RELATION].relation_changed, self._ensure_tls)
        # Relation handlers are initialized before self.certificates as we need them when calling
        # self._get_certificate_requests()
        self._ingress_provider = IngressPerAppProvider(charm=self, relation_name=INGRESS_RELATION)
        self._ingress_per_unit_provider = IngressPerUnitProvider(charm=self)
        self.reverseproxy_requirer = HTTPRequirer(self, REVERSE_PROXY_RELATION)
        self.haproxy_route_provider = HaproxyRouteProvider(self)
        self.certificates = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name=TLS_CERT_RELATION,
            certificate_requests=self._get_certificate_requests(),
            refresh_events=[
                self.on.config_changed,
                self.haproxy_route_provider.on.data_available,
                self.haproxy_route_provider.on.data_removed,
            ],
            mode=Mode.UNIT,
        )

        self._tls = TLSRelationService(self.model, self.certificates)
        self.website_requirer = HTTPProvider(self, WEBSITE_RELATION)

        self._grafana_agent = COSAgentProvider(
            self,
            metrics_endpoints=[
                {"path": "/metrics", "port": 9123},
            ],
            dashboard_dirs=["./src/grafana_dashboards"],
        )

        self.hacluster = HAServiceRequires(self, HACLUSTER_INTEGRATION)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.upgrade_charm, self._on_install)
        self.framework.observe(self.on.get_certificate_action, self._on_get_certificate_action)
        self.framework.observe(
            self.certificates.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self.reverseproxy_requirer.on.http_backend_available, self._on_http_backend_available
        )
        self.framework.observe(
            self.reverseproxy_requirer.on.http_backend_removed, self._on_http_backend_removed
        )
        self.framework.observe(
            self._ingress_provider.on.data_provided, self._on_ingress_data_provided
        )
        self.framework.observe(
            self._ingress_provider.on.data_removed, self._on_ingress_data_removed
        )
        self.framework.observe(
            self._ingress_per_unit_provider.on.data_provided,
            self._on_ingress_per_unit_data_provided,
        )
        self.framework.observe(
            self._ingress_per_unit_provider.on.data_removed, self._on_ingress_data_removed
        )
        self.framework.observe(self.hacluster.on.ha_ready, self._on_config_changed)
        self.framework.observe(
            self.haproxy_route_provider.on.data_available, self._on_config_changed
        )
        self.framework.observe(
            self.haproxy_route_provider.on.data_removed, self._on_config_changed
        )

    @validate_config_and_tls(defer=False)
    def _on_install(self, _: typing.Any) -> None:
        """Install the haproxy service and reconcile."""
        self.haproxy_service.install()
        self._reconcile()

    @validate_config_and_tls(defer=False)
    def _on_config_changed(self, _: typing.Any) -> None:
        """Handle the config-changed event."""
        self._reconcile()

    @validate_config_and_tls(defer=True)
    def _on_certificate_available(self, _: CertificateAvailableEvent) -> None:
        """Handle the TLS Certificate available event."""
        self._reconcile()

    def _on_get_certificate_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-certificate` Juju action.

        Args:
            event: Juju event
        """
        TLSInformation.validate(self, self.certificates)

        hostname = event.params["hostname"]
        if provider_cert := self._tls.get_provider_cert_with_hostname(hostname):
            event.set_results(
                {
                    "certificate": provider_cert.certificate,
                    "ca": provider_cert.ca,
                    "chain": "\n\n".join([str(cert) for cert in provider_cert.chain]),
                }
            )
            return

        event.fail(f"Missing or incomplete certificate data for {hostname}")

    @validate_config_and_tls(defer=False)
    def _on_http_backend_available(self, _: HTTPBackendAvailableEvent) -> None:
        """Handle http_backend_available event for reverseproxy integration."""
        self._reconcile()

    @validate_config_and_tls(defer=False)
    def _on_http_backend_removed(self, _: HTTPBackendRemovedEvent) -> None:
        """Handle data_removed event for reverseproxy integration."""
        self._reconcile()

    def _reconcile(self) -> None:
        """Render the haproxy config and restart the service."""
        self.unit.status = ops.MaintenanceStatus("Configuring haproxy.")
        charm_state = CharmState.from_charm(
            self,
            self._ingress_provider,
            self._ingress_per_unit_provider,
            self.haproxy_route_provider,
            self.reverseproxy_requirer,
        )
        proxy_mode = charm_state.mode
        if proxy_mode == ProxyMode.INVALID:
            # We don't raise any exception/set status here as it should already be handled
            # by the _validate_state method
            return

        ha_information = HAInformation.from_charm(self)
        self._reconcile_ha(ha_information)

        match proxy_mode:
            case ProxyMode.INGRESS:
                self._configure_ingress(charm_state, IngressRequirersInformation)
            case ProxyMode.INGRESS_PER_UNIT:
                self._configure_ingress(charm_state, IngressPerUnitRequirersInformation)
            case ProxyMode.LEGACY:
                self._configure_legacy(charm_state)
            case ProxyMode.HAPROXY_ROUTE:
                self._configure_haproxy_route(charm_state)
            case _:
                if self.model.get_relation(TLS_CERT_RELATION):
                    # Reconcile certificates in case the certificates relation is present
                    tls_information = TLSInformation.from_charm(self, self.certificates)
                    self._tls.certificate_available(tls_information)

                self.unit.set_ports(80)
                self.haproxy_service.reconcile_default(charm_state)
        self.unit.status = ops.ActiveStatus()

    def _configure_ingress(
        self,
        charm_state: CharmState,
        requirer_class: IngressRequirersInformation | IngressPerUnitRequirersInformation,
    ) -> None:
        """Configure the ingress or ingress-per-unit relation."""
        tls_information = TLSInformation.from_charm(self, self.certificates)
        self._tls.certificate_available(tls_information)

        ingress_provider = (
            self._ingress_provider
            if requirer_class is IngressRequirersInformation
            else self._ingress_per_unit_provider
        )
        ingress_requirers_information = requirer_class.from_provider(ingress_provider)
        self.unit.set_ports(80, 443)
        self.haproxy_service.reconcile_ingress(
            charm_state, ingress_requirers_information, tls_information.hostnames[0]
        )

    def _configure_legacy(self, charm_state: CharmState) -> None:
        """Configure the legacy mode."""
        if self.model.get_relation(TLS_CERT_RELATION):
            # Reconcile certificates in case the certificates relation is present
            tls_information = TLSInformation.from_charm(self, self.certificates)
            self._tls.certificate_available(tls_information)

        legacy_invalid_requested_port: list[str] = []
        required_ports: set[Port] = set()
        for service in self.reverseproxy_requirer.get_services_definition().values():
            port = service["service_port"]
            if not _validate_port(port):
                logger.error("Requested port: %s is not a valid tcp port. Skipping", port)
                legacy_invalid_requested_port.append(f"{service['service_name']:{port}}")
                continue
            required_ports.add(Port(protocol="tcp", port=port))

        if legacy_invalid_requested_port:
            error_msg = f"Invalid ports requested: {','.join(legacy_invalid_requested_port)}"
            raise ReverseProxyInvalidPortError(error_msg)

        self.unit.set_ports(*required_ports)
        self.haproxy_service.reconcile_legacy(
            charm_state, self.reverseproxy_requirer.get_services()
        )

    def _configure_haproxy_route(self, charm_state: CharmState) -> None:
        """Configure the haproxy route relation."""
        tls_information = TLSInformation.from_charm(self, self.certificates)
        self._tls.certificate_available(tls_information)

        haproxy_route_requirers_information = HaproxyRouteRequirersInformation.from_provider(
            self.haproxy_route_provider,
            typing.cast(typing.Optional[str], self.model.config.get("external-hostname")),
            self._get_peer_units_address(),
        )
        self.haproxy_service.reconcile_haproxy_route(
            charm_state, haproxy_route_requirers_information
        )
        self.unit.set_ports(80, 443)
        if self.unit.is_leader():
            for backend in haproxy_route_requirers_information.backends:
                relation = self.model.get_relation(HAPROXY_ROUTE_RELATION, backend.relation_id)
                if not relation:
                    logger.error("Relation does not exist, skipping.")
                    break
                paths = backend.application_data.paths if backend.path_acl_required else [""]
                self.haproxy_route_provider.publish_proxied_endpoints(
                    [
                        f"https://{hostname}/{path}"
                        for hostname in backend.hostname_acls
                        for path in paths
                    ],
                    relation,
                )
            for relation_id in haproxy_route_requirers_information.relation_ids_with_invalid_data:
                if relation := self.model.get_relation(HAPROXY_ROUTE_RELATION, relation_id):
                    self.haproxy_route_provider.publish_proxied_endpoints([], relation)

    def _get_certificate_requests(self) -> typing.List[CertificateRequestAttributes]:
        """Get the certificate requests.

        Returns:
            typing.List[CertificateRequestAttributes]: List of certificate request attributes.
        """
        external_hostname = typing.cast(str, self.config.get("external-hostname", None))

        try:
            charm_state = CharmState.from_charm(
                self,
                self._ingress_provider,
                self._ingress_per_unit_provider,
                self.haproxy_route_provider,
                self.reverseproxy_requirer,
            )
            proxy_mode = charm_state.mode

            if proxy_mode == ProxyMode.HAPROXY_ROUTE:
                haproxy_route_requirer_information = (
                    HaproxyRouteRequirersInformation.from_provider(
                        self.haproxy_route_provider,
                        external_hostname,
                        self._get_peer_units_address(),
                    )
                )
                return [
                    CertificateRequestAttributes(
                        common_name=hostname_acl, sans_dns=frozenset([hostname_acl])
                    )
                    for backend in haproxy_route_requirer_information.backends
                    for hostname_acl in backend.hostname_acls
                ]
        except (
            HaproxyRouteIntegrationDataValidationError,
            TLSNotReadyError,
            CharmStateValidationBaseError,
            HaproxyRouteIntegrationDataValidationError,
        ):
            # We are handling errors here and not re-raising/setting charm status as
            # this method is called during charm initialization
            logger.exception("haproxy-route information not ready, skipping certificate request.")
            return []

        # If we're not in haproxy-route mode, then external-hostname
        # is used for CSRs
        if not external_hostname:
            return []

        return [
            CertificateRequestAttributes(
                common_name=external_hostname, sans_dns=frozenset([external_hostname])
            )
        ]

    @validate_config_and_tls(defer=False)
    def _on_ingress_per_unit_data_provided(self, _: IngressDataReadyEvent) -> None:
        """Handle the data-provided event for ingress-per-unit."""
        self._reconcile()
        if self.unit.is_leader():
            tls_information = TLSInformation.from_charm(self, self.certificates)
            for relation in self._ingress_per_unit_provider.relations:
                for unit in relation.units:
                    if not self._ingress_per_unit_provider.is_unit_ready(relation, unit):
                        logger.warning(
                            "Unit %s is not ready for ingress-per-unit relation, skipping.",
                            unit.name,
                        )
                        continue
                    integration_data = self._ingress_per_unit_provider.get_data(relation, unit)
                    path_prefix = f"{integration_data['model']}-{integration_data['name']}"
                    self._ingress_per_unit_provider.publish_url(
                        relation,
                        integration_data["name"],
                        f"https://{tls_information.hostnames[0]}/{path_prefix}",
                    )

    @validate_config_and_tls(defer=True)
    def _on_ingress_data_provided(self, event: IngressPerAppDataProvidedEvent) -> None:
        """Handle the data-provided event.

        Args:
            event: Juju event.
        """
        self._reconcile()
        if self.unit.is_leader():
            tls_information = TLSInformation.from_charm(self, self.certificates)
            integration_data = self._ingress_provider.get_data(event.relation)
            path_prefix = f"{integration_data.app.model}-{integration_data.app.name}"
            self._ingress_provider.publish_url(
                event.relation, f"https://{tls_information.hostnames[0]}/{path_prefix}/"
            )

    @validate_config_and_tls(defer=False)
    def _on_ingress_data_removed(
        self, _: IngressPerAppDataRemovedEvent | IngressDataRemovedEvent
    ) -> None:
        """Handle the data-removed event."""
        self._reconcile()

    def _reconcile_ha(self, ha_information: HAInformation) -> None:
        """Update ha configuration.

        Args:
            ha_information: HAInformation charm state component.
        """
        if not ha_information.ha_integration_ready:
            logger.info("ha integration is not ready, skipping.")
            return

        if not ha_information.haproxy_peer_integration_ready:
            logger.info("haproxy-peers integration is not ready, skipping.")
            return

        peer_relation = typing.cast(
            ops.model.Relation, self.model.get_relation(HAPROXY_PEER_INTEGRATION)
        )

        if ha_information.configured_vip and ha_information.configured_vip != ha_information.vip:
            self.hacluster.remove_vip(self.app.name, str(ha_information.configured_vip))

        self.hacluster.add_vip(self.app.name, str(ha_information.vip))
        self.hacluster.add_systemd_service(f"{self.app.name}-{HAPROXY_SERVICE}", HAPROXY_SERVICE)
        self.hacluster.bind_resources()
        peer_relation.data[self.unit].update({"vip": str(ha_information.vip)})

    @validate_config_and_tls(defer=True)
    def _ensure_tls(self, _: ops.EventBase) -> None:
        """Ensure that the charm is ready to handle TLS-related events."""
        TLSInformation.validate(self, self.certificates)

    def _get_peer_units_address(self) -> list[str]:
        """Get address of peer units.

        Returns:
            list[str]: The list of peer units address.
        """
        unit_address = self._get_unit_address()
        if not unit_address:
            raise HaproxyUnitAddressNotAvailableError(
                "Couldn't get the executing unit's IP address."
            )
        peer_units_address: list[str] = [unit_address]
        if haproxy_peer_integration := self.model.get_relation(HAPROXY_PEER_INTEGRATION):
            for unit in haproxy_peer_integration.units:
                if unit != self.unit:
                    if peer_unit_address := haproxy_peer_integration.data[unit].get(
                        "private-address"
                    ):
                        peer_units_address.append(peer_unit_address)
                    else:
                        logger.warning("Cannot get address for peer unit: %s. Skipping", unit)
        return peer_units_address

    def _get_unit_address(self) -> typing.Optional[str]:
        """Get the current unit's address.

        Returns:
            Optional[str]: The unit's address from juju-info binding,
                or None if the address cannot be fetched
        """
        network_binding = self.model.get_binding("juju-info")
        if (
            network_binding is not None
            and (bind_address := network_binding.network.bind_address) is not None
        ):
            return str(bind_address)
        return None


if __name__ == "__main__":  # pragma: nocover
    ops.main(HAProxyCharm)
