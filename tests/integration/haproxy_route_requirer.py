# pylint: disable=import-error,duplicate-code,wrong-import-position
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""haproxy-route requirer source."""

import sys

# The last one is the dynamic modules. That way we get the new cryptography
# library, not the system one.
sys.path.insert(0, sys.path[-1])

import logging  # noqa: E402
import pathlib  # noqa: E402
import subprocess  # noqa: E402  # nosec: B404
from subprocess import CalledProcessError  # noqa: E402  # nosec: B404

import apt  # noqa: E402
import ops  # noqa: E402
from any_charm_base import AnyCharmBase  # noqa: E402
from haproxy_route import HaproxyRouteRequirer  # noqa: E402
from tls_certificates import (  # noqa: E402
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
        """Initialize the requirer charm."""  # noqa
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

    def start_ssl_server(self):
        """Start apache2 webserver."""
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "index.html"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")

        ssl_host = f"""
        <VirtualHost *:443>
                ServerAdmin webmaster@localhost
                DocumentRoot /var/www/html
                ErrorLog ${{APACHE_LOG_DIR}}/error.log
                CustomLog ${{APACHE_LOG_DIR}}/access.log combined
                SSLEngine on
                SSLCertificateFile      {str(SSL_CERT_FILE)}
                SSLCertificateKeyFile   {str(SSL_PRIVATE_KEY_FILE)}
        </VirtualHost>

        # This easier that editing an apache config file to comment the "Listen 80" line.
        <VirtualHost *:80>
                RewriteEngine On
                RewriteRule .* - [R=503,L]
        </VirtualHost>
        """
        ssl_site_file = pathlib.Path("/etc/apache2/sites-available/anycharm-ssl.conf")
        ssl_site_file.write_text(ssl_host, encoding="utf-8")
        self._run_subprocess(["a2dissite", "000-default"])
        self._run_subprocess(["a2ensite", "anycharm-ssl"])
        self._run_subprocess(["a2enmod", "ssl", "rewrite"])
        self._run_subprocess(["systemctl", "restart", "apache2"])
        self.unit.status = ops.ActiveStatus("SSL Server ready")

    def _run_subprocess(self, cmd: list[str]):
        """Run a subprocess command.

        Args:
          cmd: command to execute

        Raises:
          CalledProcessError: Error running the command.
        """
        try:
            subprocess.run(cmd, capture_output=True, check=True)  # nosec: B603
        except CalledProcessError as e:
            logging.error(
                "%s:\nstdout:\n%s\nstderr:\n%s",
                " ".join(cmd),
                e.stdout.decode(),
                e.stderr.decode(),
            )
            raise

    def update_relation(self, haproxy_route_params: dict[str, str]):
        """Update relation details for haproxy-route.

        Args:
          haproxy_route_params: arguments to pass relation.
        """
        self._haproxy_route.provide_haproxy_route_requirements(**haproxy_route_params)
