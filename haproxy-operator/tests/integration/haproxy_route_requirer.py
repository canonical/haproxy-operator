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

        self._grpc_server = None

    def start_server(self, grpc: bool = False):
        """Start apache2 webserver or gRPC server."""
        if grpc:
            self._start_grpc_server(port=50051, use_tls=False)
            self.unit.status = ops.ActiveStatus("gRPC Server ready")
            return

        self._start_apache_server()

    def _start_apache_server(self):
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "index.html"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")
        self.unit.status = ops.ActiveStatus("Server ready")

    def start_ssl_server(self, protocols: str | None = None, grpc: bool = False):
        """Start apache2 webserver or gRPC server with TLS.

        Args:
            protocols: Apache Protocols directive value (e.g., "h2", "http/1.1", "h2 http/1.1").
            grpc: If True, start gRPC server instead of apache2.
        """
        if grpc:
            self._start_grpc_server(port=50051, use_tls=True)
            self.unit.status = ops.ActiveStatus("gRPC SSL Server ready")
            return

        self._start_apache2_ssl_server(protocols)
        self.unit.status = ops.ActiveStatus("SSL Server ready")

    def _start_apache2_ssl_server(self, protocols):
        apt.update()
        apt.add_package(package_names="apache2")
        www_dir = pathlib.Path("/var/www/html")
        file_path = www_dir / "index.html"
        file_path.parent.mkdir(exist_ok=True)
        file_path.write_text("ok!")

        protocols_line = f"Protocols {protocols}" if protocols else ""
        ssl_host = textwrap.dedent(f"""
            LogFormat "%{{X-Request-ID}}i %h %l %u %t \\"%r\\" %>s %O \\"%{{Referer}}i\\" \\"%{{User-Agent}}i\\"" combined_with_id
            <VirtualHost *:443>
                    ServerAdmin webmaster@localhost
                    DocumentRoot /var/www/html
                    ErrorLog ${{APACHE_LOG_DIR}}/error.log
                    CustomLog ${{APACHE_LOG_DIR}}/access.log combined_with_id
                    SSLEngine on
                    SSLCertificateFile      {SSL_CERT_FILE!s}
                    SSLCertificateKeyFile   {SSL_PRIVATE_KEY_FILE!s}
                    {protocols_line}
            </VirtualHost>
            # This easier that editing an apache config file to comment the "Listen 80" line.
            <VirtualHost *:80>
                    RewriteEngine On
                    RewriteRule .* - [R=503,L]
            </VirtualHost>
            """)
        ssl_site_file = pathlib.Path("/etc/apache2/sites-available/anycharm-ssl.conf")
        ssl_site_file.write_text(ssl_host, encoding="utf-8")
        commands = [
            ["a2dissite", "000-default"],
            ["a2ensite", "anycharm-ssl"],
            ["a2enmod", "ssl", "rewrite"],
            ["systemctl", "restart", "apache2"],
        ]
        for command in commands:
            self._run_subprocess(command)

    def _run_subprocess(self, cmd: list[str]):
        """Run a subprocess command.

        Args:
          cmd: command to execute

        Raises:
          CalledProcessError: Error running the command.
        """
        try:
            # Safe because command is constructed as a list,
            # not using shell=True, and contains no user input
            subprocess.run(cmd, capture_output=True, check=True)  # nosec: subprocess_without_shell
        except CalledProcessError as e:
            logging.error(
                "%s:\nstdout:\n%s\nstderr:\n%s",
                " ".join(cmd),
                e.stdout.decode(),
                e.stderr.decode(),
            )
            raise

    def update_relation(self, haproxy_route_params: dict[str, Any]):
        """Update relation details for haproxy-route.

        Args:
          haproxy_route_params: arguments to pass relation.
        """
        self._haproxy_route.provide_haproxy_route_requirements(**haproxy_route_params)

    def enable_http2(self) -> None:
        """Enable HTTP/2 support in the apache2 webserver."""
        commands = [
            ["a2enmod", "http2"],
            ["systemctl", "restart", "apache2"],
        ]
        for command in commands:
            self._run_subprocess(command)

    def disable_http2(self) -> None:
        """Disable HTTP/2 support in the apache2 webserver."""
        commands = [
            ["a2dismod", "http2"],
            ["systemctl", "restart", "apache2"],
        ]
        for command in commands:
            self._run_subprocess(command)

    def _start_grpc_server(self, port: int = 50051, use_tls: bool = False):
        """Start the gRPC server in the background.

        Args:
            port: Port to listen on
            use_tls: Whether to use TLS
        """
        charm_dir = next(pathlib.Path("/var/lib/juju/agents").glob("unit-*/charm"))
        dynamic_packages = charm_dir / "dynamic-packages"
        src_dir = charm_dir / "src"

        cmd = ["python3", "-m", "grpc_server", "--port", str(port)]
        if use_tls:
            cmd.extend(["--tls", "--cert", str(SSL_CERT_FILE), "--key", str(SSL_PRIVATE_KEY_FILE)])

        # Safe because command is constructed as a list,
        # not using shell=True, and contains no user input
        subprocess.Popen(  # nosec: subprocess_without_shell
            cmd,
            cwd=str(src_dir),
            env={
                "PYTHONPATH": f"{dynamic_packages}:{src_dir}",
            },
            start_new_session=True,
        )
