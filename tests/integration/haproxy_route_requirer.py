# pylint: disable=import-error,duplicate-code,wrong-import-position
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import sys
from typing import Any

# The last one is the dynamic modules. That way we get the new cryptography
# library, not the system one.
sys.path.insert(0, sys.path[-1])

import logging
import pathlib
import subprocess  # nosec: B404
import textwrap
from subprocess import CalledProcessError  # nosec: B404

import apt
import ops
from any_charm_base import AnyCharmBase
from haproxy_route import HaproxyRouteRequirer
from tls_certificates import (
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)

HAPROXY_ROUTE_RELATION = "require-haproxy-route"
TLS_CERT_RELATION = "require-tls-certificates"

SSL_CERT_FILE = pathlib.Path("/etc/ssl/certs/ssl-cert-anycharm.pem")
SSL_PRIVATE_KEY_FILE = pathlib.Path("/etc/ssl/private/ssl-cert-anycharm.key")


class AnyCharm(AnyCharmBase):
    """haproxy-route requirer charm."""

    def __init__(self, *args, **kwargs):
        """Initialize the requirer charm."""
        super().__init__(*args, **kwargs)
        self._haproxy_route = HaproxyRouteRequirer(self, HAPROXY_ROUTE_RELATION)
        network_binding = self.model.get_binding(TLS_CERT_RELATION)
        bind_address = network_binding.network.bind_address
        self.certificates = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name=TLS_CERT_RELATION,
            certificate_requests=[
                CertificateRequestAttributes(
                    common_name="any-charm-haproxy-route-requirer",
                    sans_dns=frozenset(["any-charm-haproxy-route-requirer", str(bind_address)]),
                )
            ],
            refresh_events=[self.on.config_changed],
            mode=Mode.UNIT,
        )

        provider_certificates, private_key = self.certificates.get_assigned_certificates()
        if provider_certificates:
            SSL_PRIVATE_KEY_FILE.write_text(str(private_key), encoding="utf-8")
            for provider_certificate in provider_certificates:
                SSL_CERT_FILE.write_text(str(provider_certificate.certificate), encoding="utf-8")

    def start_server(self):
        """Start apache2 webserver."""
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "index.html"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")
        self.unit.status = ops.ActiveStatus("Server ready")

    def update_relation(self, haproxy_route_params: dict[str, Any]):
        """Update relation details for haproxy-route.

        Args:
          haproxy_route_params: arguments to pass relation.
        """
        self._haproxy_route.provide_haproxy_route_requirements(**haproxy_route_params)
