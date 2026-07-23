#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""haproxy-operator charm file."""

import json
import logging
import typing

import ops
from charmlibs.interfaces.tls_certificates import (
    CertificateAvailableEvent,
    CertificateRequestAttributes,
    Mode,
    PrivateKey,
    TLSCertificatesRequiresV4,
)
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificatesAvailableEvent,
    CertificatesRemovedEvent,
    CertificateTransferRequires,
)
from charms.grafana_agent.v0.cos_agent import COSAgentProvider
from charms.haproxy.v0.ddos_protection import (
    DDOS_PROTECTION_RELATION_NAME,
    DDoSProtectionRequirer,
)
from charms.haproxy.v0.spoe_auth import SpoeAuthRequirer
from charms.haproxy.v1.haproxy_route_tcp import HaproxyRouteTcpProvider
from charms.haproxy.v2.haproxy_route import HaproxyRouteProvider
from charms.haproxy_route_policy.v0.haproxy_route_policy import HaproxyRoutePolicyRequirer
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
from ops.model import Port, SecretNotFoundError

from haproxy import HAPROXY_CONFIG, HAPROXY_SERVICE, HAProxyService, file_exists, read_file
from http_interface import (
    HTTPBackendAvailableEvent,
    HTTPBackendRemovedEvent,
    HTTPProvider,
    HTTPRequirer,
)
from state.charm_state import CharmState, ProxyMode
from state.ddos_protection import DDosProtection
from state.exception import CharmStateValidationBaseError
from state.ha import HACLUSTER_INTEGRATION, HAPROXY_PEER_INTEGRATION, HAInformation
from state.haproxy_route import (
    HAPROXY_ROUTE_RELATION,
    HAProxyRouteBackend,
    HaproxyRouteIntegrationDataValidationError,
    HaproxyRouteRequirersInformation,
)
from state.ingress import IngressRequirersInformation
from state.ingress_per_unit import IngressPerUnitRequirersInformation
from state.spoe_auth import SpoeAuthInformation
from state.tls import (
    SHARED_PRIVATE_KEY_SECRET_LABEL,
    TLSInformation,
    TLSNotReadyError,
    haproxy_peer_relation_app_data_encoder,
)
from state.validation import validate_config_and_tls
from tls_relation import TLSRelationService

logger = logging.getLogger(__name__)

INGRESS_RELATION = "ingress"
TLS_CERT_RELATION = "certificates"
REVERSE_PROXY_RELATION = "reverseproxy"
WEBSITE_RELATION = "website"
RECV_CA_CERTS_RELATION = "receive-ca-certs"
SPOE_AUTH_RELATION = "spoe-auth"
HAPROXY_ROUTE_TCP_RELATION = "haproxy-route-tcp"
HAPROXY_ROUTE_POLICY_RELATION_NAME = "haproxy-route-policy"


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


def _strip_shared_boundaries(configuration: str, reference: str) -> str:
    """Remove the leading and trailing lines ``configuration`` shares with ``reference``.

    Keeps everything between the first and last differing line, so
    operator-specific content is never dropped. Returns the input verbatim when
    nothing is shared at the boundaries.

    Args:
        configuration: The configuration to trim.
        reference: The reference configuration to compare against.

    Returns:
        The trimmed configuration.
    """
    config_lines = configuration.splitlines()
    reference_lines = reference.splitlines()

    start = 0
    while (
        start < len(config_lines)
        and start < len(reference_lines)
        and config_lines[start] == reference_lines[start]
    ):
        start += 1

    config_end = len(config_lines)
    reference_end = len(reference_lines)
    while (
        config_end > start
        and reference_end > start
        and config_lines[config_end - 1] == reference_lines[reference_end - 1]
    ):
        config_end -= 1
        reference_end -= 1

    if start == 0 and config_end == len(config_lines):
        return configuration
    return "\n".join(config_lines[start:config_end])


def _is_section_header(line: str) -> bool:
    """Return whether a line starts a new haproxy config section.

    Args:
        line: A single configuration line.

    Returns:
        True if the line begins a section.
    """
    return bool(line) and not line[0].isspace() and not line.lstrip().startswith("#")


def _split_config_sections(configuration: str) -> list[list[str]]:
    """Split an haproxy configuration into its sections, preserving lines verbatim.

    Each section is a header line plus every line beneath it, up to (but not
    including) the next header.

    Args:
        configuration: The haproxy configuration text.

    Returns:
        A list of sections, each the list of lines it contains.
    """
    sections: list[list[str]] = []
    current: list[str] = []
    for line in configuration.splitlines():
        # A new header means the section we were accumulating is finished.
        if _is_section_header(line) and current:
            sections.append(current)
            current = []
        current.append(line)
    if current:
        sections.append(current)
    return sections


def _filter_config_by_backend(configuration: str, backend_name: str) -> str:
    """Return the ``backend <name>`` section(s) for ``backend_name``.

    A section-aware alternative to grepping the output: a section is matched only
    by its header (``backend <name>``).

    Args:
        configuration: The haproxy configuration text.
        backend_name: The backend name to filter for.

    Returns:
        The matching ``backend`` section(s), or "" if none match.
    """
    matched = []
    for section in _split_config_sections(configuration):
        tokens = section[0].split()
        if len(tokens) >= 2 and tokens[0] == "backend" and tokens[1] == backend_name:
            matched.append(section)
    return "\n".join("\n".join(section) for section in matched)


def _config_backend_names(configuration: str) -> list[str]:
    """Return the names of every ``backend`` section in the configuration.

    Args:
        configuration: The haproxy configuration text.

    Returns:
        The backend names, in the order they appear.
    """
    names: list[str] = []
    for section in _split_config_sections(configuration):
        tokens = section[0].split()
        if len(tokens) >= 2 and tokens[0] == "backend":
            names.append(tokens[1])
    return names


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
        self.haproxy_route_tcp_provider = HaproxyRouteTcpProvider(self)
        self.spoe_auth_requirer = SpoeAuthRequirer(self, SPOE_AUTH_RELATION)
        self.ddos_requirer = DDoSProtectionRequirer(self)
        self.haproxy_route_policy = HaproxyRoutePolicyRequirer(
            self, HAPROXY_ROUTE_POLICY_RELATION_NAME
        )
        self.recv_ca_certs = CertificateTransferRequires(self, RECV_CA_CERTS_RELATION)
        self.certificates = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name=TLS_CERT_RELATION,
            certificate_requests=self._get_certificate_requests(),
            refresh_events=[
                self.on.config_changed,
                self.haproxy_route_provider.on.data_available,
                self.haproxy_route_provider.on.data_removed,
                self.haproxy_route_tcp_provider.on.data_available,
                self.haproxy_route_tcp_provider.on.data_removed,
                # We also need to refresh on spoe-auth and haproxy-route-policy relation changes
                # as they also contribute to the list of certificate requests.
                self.on[SPOE_AUTH_RELATION].relation_changed,
                self.on[SPOE_AUTH_RELATION].relation_broken,
                self.on[HAPROXY_ROUTE_POLICY_RELATION_NAME].relation_changed,
                self.on[HAPROXY_ROUTE_POLICY_RELATION_NAME].relation_broken,
            ],
            mode=Mode.APP,
            private_key=self._ensure_private_key(),
        )

        self._tls = TLSRelationService(self.model, self.certificates, self.recv_ca_certs)
        self.website_requirer = HTTPProvider(self, WEBSITE_RELATION)

        self._grafana_agent = COSAgentProvider(
            self,
            metrics_endpoints=[
                {"path": "/metrics", "port": 8404},
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
            self.recv_ca_certs.on.certificate_set_updated, self._on_ca_certificates_updated
        )
        self.framework.observe(
            self.recv_ca_certs.on.certificates_removed, self._on_ca_certificates_removed
        )
        self.framework.observe(
            self.haproxy_route_provider.on.data_available, self._on_config_changed
        )
        self.framework.observe(
            self.haproxy_route_provider.on.data_removed, self._on_config_changed
        )
        self.framework.observe(
            self.haproxy_route_tcp_provider.on.data_available, self._on_config_changed
        )
        self.framework.observe(
            self.haproxy_route_tcp_provider.on.data_removed, self._on_config_changed
        )
        self.framework.observe(
            self.on.get_proxied_endpoints_action, self._on_get_proxied_endpoints_action
        )
        self.framework.observe(self.on.get_configuration_action, self._on_get_configuration_action)
        # Hook peer relation events so non-leader units reconcile when the leader
        # publishes certificate data to the peer relation app databag.
        self.framework.observe(
            self.on[HAPROXY_PEER_INTEGRATION].relation_changed, self._on_config_changed
        )
        self.framework.observe(
            self.on[HAPROXY_PEER_INTEGRATION].relation_joined, self._on_config_changed
        )
        # Hook relation-related events to the reconcile loop.
        for relation in [
            SPOE_AUTH_RELATION,
            DDOS_PROTECTION_RELATION_NAME,
            HAPROXY_ROUTE_POLICY_RELATION_NAME,
        ]:
            self.framework.observe(self.on[relation].relation_changed, self._on_config_changed)
            self.framework.observe(self.on[relation].relation_broken, self._on_config_changed)

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

        hostname = event.params.get("hostname", "")
        wildcard = event.params.get("wildcard", False)
        if wildcard:
            hostname = f"*.{hostname}"
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

    def _charm_state(self) -> CharmState:
        """Build the charm state from the current charm and its providers.

        Returns:
            The charm state component.
        """
        return CharmState.from_charm(
            self,
            self._ingress_provider,
            self._ingress_per_unit_provider,
            self.haproxy_route_provider,
            self.haproxy_route_tcp_provider,
            self.reverseproxy_requirer,
            self.haproxy_route_policy,
        )

    def _reconcile(self) -> None:
        """Render the haproxy config and restart the service."""
        self.unit.status = ops.MaintenanceStatus("Configuring haproxy.")
        charm_state = self._charm_state()
        proxy_mode = charm_state.mode
        if proxy_mode == ProxyMode.INVALID:
            # We don't raise any exception/set status here as it should already be handled
            # by the _validate_state method
            return

        ha_information = HAInformation.from_charm(self)
        self._reconcile_ha(ha_information)

        status_message = ""
        match proxy_mode:
            case ProxyMode.INGRESS:
                self._configure_ingress(charm_state, IngressRequirersInformation)
            case ProxyMode.INGRESS_PER_UNIT:
                self._configure_ingress(charm_state, IngressPerUnitRequirersInformation)
            case ProxyMode.LEGACY:
                self._configure_legacy(charm_state)
            case ProxyMode.HAPROXY_ROUTE:
                status_message = self._configure_haproxy_route(charm_state, ha_information)
            case _:
                if self.model.get_relation(TLS_CERT_RELATION):
                    # Reconcile certificates in case the certificates relation is present
                    tls_information = TLSInformation.from_charm(self, self.certificates)
                    self._tls.certificate_available(tls_information)

                self.unit.set_ports(80)
                self.haproxy_service.reconcile_default(charm_state)
        self.unit.status = ops.ActiveStatus(status_message)

    def _configure_ingress(
        self,
        charm_state: CharmState,
        requirer_class: type[IngressRequirersInformation | IngressPerUnitRequirersInformation],
    ) -> None:
        """Configure the ingress or ingress-per-unit relation."""
        tls_information = TLSInformation.from_charm(self, self.certificates)
        self._tls.certificate_available(tls_information)

        ingress_provider = (
            self._ingress_provider
            if requirer_class is IngressRequirersInformation
            else self._ingress_per_unit_provider
        )
        ingress_requirers_information = requirer_class.from_provider(
            ingress_provider, self._get_peer_units_address()
        )
        ddos_protection_config = DDosProtection.from_charm(self.ddos_requirer)
        self.unit.set_ports(80, 443)
        self.haproxy_service.reconcile_ingress(
            charm_state,
            ingress_requirers_information,
            tls_information.hostnames[0],
            ddos_protection_config,
        )
        self._publish_certificate_to_peer_units(tls_information)

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

    def _configure_haproxy_route(
        self, charm_state: CharmState, ha_information: HAInformation
    ) -> str:
        """Configure the haproxy route relation.

        Returns:
            str: A status message indicating valid/total relations.
        """
        haproxy_route_requirers_information = HaproxyRouteRequirersInformation.from_provider(
            haproxy_route=self.haproxy_route_provider,
            haproxy_route_tcp=self.haproxy_route_tcp_provider,
            haproxy_route_policy=self.haproxy_route_policy,
            external_hostname=typing.cast(
                typing.Optional[str], self.model.config.get("external-hostname")
            ),
            peers=self._get_peer_units_address(),
            ca_certs_configured=bool(self.recv_ca_certs.get_all_certificates()),
        )
        if self.unit.is_leader() and self.haproxy_route_policy.relation is not None:
            self.haproxy_route_policy.provide_haproxy_route_policy_requests(
                haproxy_route_requirers_information.backend_requests_for_policy,
                haproxy_route_requirers_information.policy_provider_backend.hostname
                if haproxy_route_requirers_information.policy_provider_backend
                else None,
            )
        # We ONLY allow the charm to run with no certificate requested if:
        # 1. there's only haproxy-route-tcp relations
        # AND
        # 2. All requirers must enable TLS passthrough or disable TLS termination
        allow_no_certificates = bool(
            not haproxy_route_requirers_information.backends
            and haproxy_route_requirers_information.tcp_frontends
            and all(
                not frontend.enforce_tls or not frontend.tls_terminate
                for frontend in haproxy_route_requirers_information.tcp_frontends
            )
        )
        tls_information = TLSInformation.from_charm(self, self.certificates, allow_no_certificates)
        self._tls.certificate_available(tls_information)
        ddos_protection_config = DDosProtection.from_charm(self.ddos_requirer)

        spoe_oauth_info_list = SpoeAuthInformation.from_requirer(self.spoe_auth_requirer)

        self.haproxy_service.reconcile_haproxy_route(
            charm_state,
            haproxy_route_requirers_information,
            spoe_oauth_info_list,
            ddos_protection_config,
        )
        self.unit.set_ports(
            80,
            443,
            *(
                port
                for frontend in haproxy_route_requirers_information.valid_tcp_frontends()
                for port in frontend.covered_ports
            ),
            *(
                backend.application_data.external_grpc_port
                for backend in haproxy_route_requirers_information.valid_backends()
                if backend.application_data.external_grpc_port is not None
            ),
        )
        if self.unit.is_leader():
            self._publish_haproxy_route_proxied_endpoints(haproxy_route_requirers_information)
            self._publish_haproxy_route_tcp_proxied_endpoints(
                haproxy_route_requirers_information, ha_information
            )
            self._publish_certificate_to_peer_units(tls_information)

        return self._get_haproxy_route_status_message(haproxy_route_requirers_information)

    def _get_haproxy_route_status_message(self, info: HaproxyRouteRequirersInformation) -> str:
        """Generate a status message showing valid/total relations.

        Args:
            info: The haproxy route requirers information.

        Returns:
            str: A status message indicating valid/total relations.
        """
        total = len(self.haproxy_route_provider.relations) + len(
            self.haproxy_route_tcp_provider.relations
        )
        invalid = len(info.relation_ids_with_invalid_data) + len(
            info.relation_ids_with_invalid_data_tcp
        )
        valid = total - invalid
        if not total:
            return ""
        return f"{valid}/{total} valid relations"

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
                self.haproxy_route_tcp_provider,
                self.reverseproxy_requirer,
                self.haproxy_route_policy,
            )
            proxy_mode = charm_state.mode

            if proxy_mode == ProxyMode.HAPROXY_ROUTE:
                haproxy_route_requirer_information = (
                    HaproxyRouteRequirersInformation.from_provider(
                        haproxy_route=self.haproxy_route_provider,
                        haproxy_route_tcp=self.haproxy_route_tcp_provider,
                        haproxy_route_policy=self.haproxy_route_policy,
                        external_hostname=external_hostname,
                        peers=self._get_peer_units_address(),
                        ca_certs_configured=bool(self.recv_ca_certs.get_all_certificates()),
                    )
                )
                certificate_requests = [
                    CertificateRequestAttributes(
                        common_name=hostname_acl, sans_dns=frozenset([hostname_acl])
                    )
                    for backend in haproxy_route_requirer_information.backends
                    for hostname_acl in backend.hostname_acls
                ] + [
                    CertificateRequestAttributes(
                        common_name=backend.application_data.sni,
                        sans_dns=frozenset([backend.application_data.sni]),
                    )
                    for frontend in haproxy_route_requirer_information.tcp_frontends
                    for backend in frontend.backends
                    if backend.application_data.sni is not None
                ]
                # Add the generated hostname with subdomain of the policy charm.
                if (
                    haproxy_route_policy_backend
                    := haproxy_route_requirer_information.policy_provider_backend
                ):
                    certificate_requests.append(
                        CertificateRequestAttributes(
                            common_name=haproxy_route_policy_backend.hostname,
                            sans_dns=frozenset([haproxy_route_policy_backend.hostname]),
                        )
                    )
                return certificate_requests
        except (
            HaproxyRouteIntegrationDataValidationError,
            TLSNotReadyError,
            CharmStateValidationBaseError,
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

    @validate_config_and_tls(defer=True)
    def _on_ca_certificates_updated(self, _: CertificatesAvailableEvent) -> None:
        """Handle the CA certificates available event."""
        self._tls.update_trusted_cas()
        self._reconcile()

    @validate_config_and_tls(defer=True)
    def _on_ca_certificates_removed(self, _: CertificatesRemovedEvent) -> None:
        """Handle the CA certificates removed event."""
        self._tls.update_trusted_cas()
        self._reconcile()

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
            Optional[str]: The unit's address from haproxy-peers binding,
                or None if the address cannot be fetched
        """
        network_binding = self.model.get_binding("haproxy-peers")
        if (
            network_binding is not None
            and (bind_address := network_binding.network.bind_address) is not None
        ):
            return str(bind_address)
        return None

    def _get_backend_proxied_endpoints(self, backend: HAProxyRouteBackend) -> list[str]:
        """Get the list of proxied endpoints for a given backend.

        Args:
            backend: The HAProxyRouteBackend instance.
        """
        paths = backend.application_data.paths if backend.path_acl_required else [""]
        return [
            f"https://{hostname}{path}"
            for hostname in iter(backend.hostname_acls)
            for path in paths
        ]

    def _on_get_proxied_endpoints_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-proxied-endpoints` Juju action.

        Args:
            event: Juju event
        """
        backend_name = event.params.get("backend")
        haproxy_route_requirers_information = HaproxyRouteRequirersInformation.from_provider(
            haproxy_route=self.haproxy_route_provider,
            haproxy_route_tcp=self.haproxy_route_tcp_provider,
            haproxy_route_policy=self.haproxy_route_policy,
            external_hostname=typing.cast("str | None", self.config.get("external-hostname")),
            peers=self._get_peer_units_address(),
            ca_certs_configured=bool(self.recv_ca_certs.get_all_certificates()),
        )

        backends = haproxy_route_requirers_information.backends

        if backend_name is not None:
            backends = [backend for backend in backends if backend.backend_name == backend_name]

        proxied_endpoints = [
            proxied_endpoint
            for backend in backends
            for proxied_endpoint in self._get_backend_proxied_endpoints(backend)
        ]

        event.set_results({"endpoints": json.dumps(proxied_endpoints)})

    def _on_get_configuration_action(self, event: ActionEvent) -> None:
        """Triggered when users run the `get-configuration` Juju action.

        `source=disk` (default) returns the on-disk configuration.
        `source=relations` renders the haproxy-route configuration from the
        current relation data. Neither writes to disk nor reloads the service.
        When a haproxy-route-policy relation is present, the rendered policy
        backend reflects the policy charm's current, asynchronously-converging
        output.

        Args:
            event: Juju event
        """
        source = event.params.get("source", "disk")
        if source == "relations":
            try:
                configuration = self._recompute_haproxy_route_configuration()
            except (
                CharmStateValidationBaseError,
                HaproxyRouteIntegrationDataValidationError,
            ) as exc:
                event.fail(f"Failed to recompute configuration from relations: {exc}")
                return
            if self.haproxy_route_policy.relation is not None:
                event.log(
                    "A haproxy-route-policy relation is present; the policy backend in this "
                    "preview reflects the policy charm's current output and converges "
                    "asynchronously. Use source=disk for the authoritative applied configuration."
                )
        else:
            if not file_exists(HAPROXY_CONFIG):
                event.fail(
                    f"HAProxy configuration file {HAPROXY_CONFIG} does not exist yet. "
                    "Ensure the charm is configured and integrated before running this action."
                )
                return
            configuration = read_file(HAPROXY_CONFIG)

        backend = typing.cast(str, event.params.get("backend", "")).strip()
        if backend:
            configuration = self._filter_configuration_for_backend(configuration, backend, event)
        else:
            if self._configuration_is_default(configuration):
                event.log(
                    "The HAProxy configuration matches the default configuration. This usually "
                    "means no proxy backends are configured (e.g. no haproxy-route, ingress, or "
                    "reverseproxy relations)."
                )

            if not typing.cast(bool, event.params.get("full", False)):
                configuration = self._hide_constant_configuration(configuration, event)

        event.set_results({"configuration": configuration, "source": source})

    def _recompute_haproxy_route_configuration(self) -> str:
        """Render the haproxy-route configuration from the current relation data.

        Unlike `_configure_haproxy_route`, performs no side effects (no port
        changes, databag writes, file writes, or reload).

        Returns:
            The rendered haproxy-route configuration.
        """
        charm_state = self._charm_state()
        haproxy_route_requirers_information = HaproxyRouteRequirersInformation.from_provider(
            haproxy_route=self.haproxy_route_provider,
            haproxy_route_tcp=self.haproxy_route_tcp_provider,
            haproxy_route_policy=self.haproxy_route_policy,
            external_hostname=typing.cast("str | None", self.config.get("external-hostname")),
            peers=self._get_peer_units_address(),
            ca_certs_configured=bool(self.recv_ca_certs.get_all_certificates()),
        )
        ddos_protection_config = DDosProtection.from_charm(self.ddos_requirer)
        spoe_oauth_info_list = SpoeAuthInformation.from_requirer(self.spoe_auth_requirer)
        return self.haproxy_service.render_haproxy_route_config(
            charm_state,
            haproxy_route_requirers_information,
            spoe_oauth_info_list,
            ddos_protection_config,
        )

    def _configuration_is_default(self, configuration: str) -> bool:
        """Return whether the given configuration matches the default configuration.

        Args:
            configuration: The configuration to compare against the default.

        Returns:
            True if it is identical to the rendered default configuration.
        """
        try:
            default_configuration = self.haproxy_service.render_default_config(self._charm_state())
        except CharmStateValidationBaseError:
            return False
        return configuration == default_configuration

    def _hide_constant_configuration(self, configuration: str, event: ActionEvent) -> str:
        """Hide the constant scaffold the config shares with the default render.

        The shared head/tail (global, defaults, prometheus frontend, fallback
        backend) is derived from ``render_default_config`` rather than hard-coded
        section names, so it stays correct if the template changes. Notifies the
        user via ``event.log`` when anything is hidden.

        Args:
            configuration: The configuration to trim.
            event: Juju event, used to notify the user when content is hidden.

        Returns:
            The trimmed configuration, or the input unchanged if the default
            configuration cannot be rendered.
        """
        try:
            default_configuration = self.haproxy_service.render_default_config(self._charm_state())
        except CharmStateValidationBaseError:
            return configuration

        trimmed = _strip_shared_boundaries(configuration, default_configuration)
        if trimmed != configuration:
            event.log(
                "Constant/default config sections (global, defaults, the prometheus frontend "
                "and the fallback backend) that are identical across deployments have been "
                "hidden for readability. Re-run this action with full=true to return the "
                "complete configuration."
            )
        return trimmed

    def _filter_configuration_for_backend(
        self, configuration: str, backend_name: str, event: ActionEvent
    ) -> str:
        """Return only the ``backend <name>`` section for ``backend_name``.

        Args:
            configuration: The configuration to filter.
            backend_name: The backend name to filter for.
            event: Juju event, used to notify the caller when nothing matches.

        Returns:
            The matching sections, or "" if the backend is not present.
        """
        filtered = _filter_config_by_backend(configuration, backend_name)
        if not filtered:
            available = _config_backend_names(configuration)
            event.log(
                f"No configuration section involves a backend named '{backend_name}'. "
                + (
                    f"Backends present: {', '.join(available)}."
                    if available
                    else "No backends are configured."
                )
            )
        return filtered

    def _publish_haproxy_route_proxied_endpoints(
        self, haproxy_route_requirers_information: HaproxyRouteRequirersInformation
    ) -> None:
        """Publish the proxied endpoints for HTTP frontends."""
        for backend in haproxy_route_requirers_information.backends:
            relation = self.model.get_relation(HAPROXY_ROUTE_RELATION, backend.relation_id)
            if not relation:
                logger.error(
                    "The haproxy-route relation does not exist for this backend, skipping."
                )
                continue
            self.haproxy_route_provider.publish_proxied_endpoints(
                self._get_backend_proxied_endpoints(backend),
                relation,
            )
        for relation_id in haproxy_route_requirers_information.relation_ids_with_invalid_data:
            if relation := self.model.get_relation(HAPROXY_ROUTE_RELATION, relation_id):
                self.haproxy_route_provider.publish_proxied_endpoints([], relation)

    def _publish_haproxy_route_tcp_proxied_endpoints(
        self,
        haproxy_route_requirers_information: HaproxyRouteRequirersInformation,
        ha_information: HAInformation,
    ) -> None:
        """Publish the proxied endpoints for TCP frontends."""
        for frontend in haproxy_route_requirers_information.valid_tcp_frontends():
            for backend in frontend.backends:
                relation = self.model.get_relation(HAPROXY_ROUTE_TCP_RELATION, backend.relation_id)
                if not relation:
                    logger.error(
                        "The haproxy-route-tcp relation does not exist for this backend, skipping."
                    )
                    continue
                if frontend.is_sni_routing_enabled:
                    self.haproxy_route_tcp_provider.publish_proxied_endpoints(
                        [f"{backend.application_data.sni}:{frontend.port}"], relation
                    )
                    continue
                if ha_information.ha_integration_ready:
                    self.haproxy_route_tcp_provider.publish_proxied_endpoints(
                        [f"{ha_information.vip}:{frontend.port}"], relation
                    )
                    continue
                self.haproxy_route_tcp_provider.publish_proxied_endpoints(
                    [
                        f"{unit_address}:{frontend.port}"
                        for unit_address in self._get_peer_units_address()
                    ],
                    relation,
                )

    def _ensure_private_key(self) -> PrivateKey | None:
        """Ensure that a private key exists as a secret before passing it to the lib."""
        if not self.unit.is_leader():
            return None
        try:
            secret = self.model.get_secret(label=SHARED_PRIVATE_KEY_SECRET_LABEL)
            return PrivateKey.from_string(secret.get_content(refresh=True)["private-key"])
        except SecretNotFoundError:
            private_key = PrivateKey.generate()
            self.app.add_secret(
                label=SHARED_PRIVATE_KEY_SECRET_LABEL,
                content={
                    "private-key": str(private_key),
                },
            )
            return private_key

    def _publish_certificate_to_peer_units(self, tls_information: TLSInformation) -> None:
        """Publish the certificate and CA chain to peer units via the peer relation."""
        if not self.unit.is_leader():
            return

        if peer_relation := self.model.get_relation(HAPROXY_PEER_INTEGRATION):
            peer_relation.save(
                obj=tls_information.tls_cert_and_ca_chain,
                dst=self.app,
                encoder=haproxy_peer_relation_app_data_encoder,
            )


if __name__ == "__main__":  # pragma: nocover
    ops.main(HAProxyCharm)
