# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for legacy integration tests."""

import ipaddress
import json
import logging
import pathlib
import tempfile
import textwrap
from urllib.parse import ParseResult, urlparse

import jubilant
import pytest
from opcli.pytest_plugin import CharmPathList
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES, HTTPAdapter

logger = logging.getLogger(__name__)

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/legacy/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "lib/charms/haproxy/v2/haproxy_route.py"
APT_LIB_SRC = "lib/charms/operator_libs_linux/v0/apt.py"


@pytest.fixture(scope="module", name="charm")
def charm_fixture(charm_paths: dict[str, CharmPathList]) -> str:
    """Get path to the haproxy charm."""
    return charm_paths["haproxy"].path


@pytest.fixture(scope="module", name="application")
def application_fixture(pytestconfig: pytest.Config, charm: str, juju: jubilant.Juju) -> str:
    """Deploy the charm.

    Args:
        pytestconfig: Pytest configuration.
        charm: Path to the packed charm file.
        juju: Jubilant juju fixture.

    Returns:
        The haproxy app name.
    """
    app_name = "haproxy"
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        logger.warning("Using existing application: %s", app_name)
        return app_name
    juju.deploy(charm, trust=True, app=app_name)
    juju.wait(lambda status: jubilant.all_active(status, app_name))
    return app_name


@pytest.fixture(scope="module", name="certificate_provider_application")
def certificate_provider_application_fixture(
    pytestconfig: pytest.Config,
    juju: jubilant.Juju,
) -> str:
    """Deploy self-signed-certificates.

    Args:
        pytestconfig: Pytest configuration.
        juju: Jubilant juju fixture.

    Returns:
        The self-signed-certificates app name.
    """
    app_name = "self-signed-certificates"
    if pytestconfig.getoption("--no-deploy") and app_name in juju.status().apps:
        logger.warning("Using existing application: %s", app_name)
        return app_name
    juju.deploy("self-signed-certificates", channel="1/edge", app=app_name)
    return app_name


@pytest.fixture(scope="module", name="configured_application_with_tls")
def configured_application_with_tls_fixture(
    application: str,
    certificate_provider_application: str,
    juju: jubilant.Juju,
) -> str:
    """The haproxy charm configured and integrated with TLS provider.

    Args:
        application: The haproxy application name.
        certificate_provider_application: The certificate provider app name.
        juju: Jubilant juju fixture.

    Returns:
        The haproxy application name.
    """
    juju.config(application, {"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    juju.integrate(
        f"{application}:certificates",
        f"{certificate_provider_application}:certificates",
    )
    juju.wait(
        lambda status: jubilant.all_active(status, application, certificate_provider_application),
    )
    return application


def get_unit_ip_address(
    juju: jubilant.Juju,
    application: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Get the unit address to make HTTP requests.

    Args:
        juju: The Jubilant juju instance.
        application: The deployed application name.

    Returns:
        The unit address.
    """
    status = juju.status()
    app_status = status.apps.get(application)
    assert app_status, f"Application {application} not found in model status"
    unit_status = next(iter(app_status.units.values()))
    address = unit_status.public_address
    assert address, f"Unit of {application} has no public address"
    return ipaddress.ip_address(address)


def get_unit_address(juju: jubilant.Juju, application: str) -> str:
    """Get the HTTP URL for the first unit of a Juju application.

    Args:
        juju: The Jubilant juju instance.
        application: The deployed application name.

    Returns:
        The unit base HTTP URL.
    """
    unit_ip_address = get_unit_ip_address(juju, application)
    url = f"http://{unit_ip_address!s}"
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        url = f"http://[{unit_ip_address!s}]"
    return url


def get_ingress_url_for_application(juju: jubilant.Juju, app_name: str) -> ParseResult:
    """Get the ingress url from the requirer's unit data.

    Args:
        juju: The Jubilant juju instance.
        app_name: Requirer application name.

    Returns:
        The parsed ingress url.
    """
    unit_name = f"{app_name}/0"
    result = juju.cli("show-unit", unit_name, "--format", "json")
    unit_information = json.loads(result)[unit_name]
    ingress_integration_data = json.loads(
        unit_information["relation-info"][0]["application-data"]["ingress"]
    )
    return urlparse(ingress_integration_data["url"])


@pytest.fixture(scope="module", name="any_charm_src")
def any_charm_src_fixture() -> dict[str, str]:
    """Any-charm configuration to test with haproxy."""
    any_charm_py = textwrap.dedent(
        """\
        import pathlib
        import ops
        from any_charm_base import AnyCharmBase
        import apt
        from subprocess import STDOUT, check_call
        import os
        import textwrap

        nginx_config = textwrap.dedent(
            \"\"\"
                events {}
                http {
                    server {
                        listen 8000;
                        location /  {
                            add_header Content-Type text/plain;
                            return 200 'default server healthy';
                        }
                    }

                    server {
                        listen 8001;
                        location /server1/health {
                            add_header Content-Type text/plain;
                            return 200 'server 1 healthy';
                        }
                    }
                }
            \"\"\"
        )
        relation_data = textwrap.dedent(
            \"\"\"
                - service_name: my_web_app
                  service_host: 0.0.0.0
                  service_port: 8994
                  service_options:
                  - mode http
                  - timeout client 300000
                  - timeout server 300000
                  - balance leastconn
                  - option httpchk HEAD / HTTP/1.0
                  - acl server1 path_beg -i /server1/health
                  - use_backend server1 if server1
                  servers:
                  - - default
                    - %s
                    - 8000
                    - check
                  backends:
                  - backend_name: server1
                    servers:
                    - - server1
                      - %s
                      - 8001
                      - check
            \"\"\"
        )

        class AnyCharm(AnyCharmBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            @property
            def bind_address(self) -> str:
                if bind := self.model.get_binding("juju-info"):
                    return str(bind.network.bind_address)
                return ""

            def update_relation_data(self):
                relation = self.model.get_relation("provide-http")
                bind_address = self.bind_address
                relation.data[self.unit].update(
                    {
                        "services": relation_data % (bind_address, bind_address),
                        "hostname": "", "port": ""
                    }
                )

            def start_server(self):
                check_call(
                    ['apt-get', 'install', '-y', 'nginx'],
                    stdout=open(os.devnull,'wb'),
                    stderr=STDOUT
                )
                www_dir = pathlib.Path("/var/www/html")
                pathlib.Path("/etc/nginx/nginx.conf").write_text(nginx_config, encoding="utf-8")
                check_call(['nginx', '-T'], stdout=open(os.devnull,'wb'), stderr=STDOUT)
                check_call(
                    ['systemctl', 'restart', 'nginx'],
                    stdout=open(os.devnull,'wb'),
                    stderr=STDOUT
                )

                self.unit.status = ops.ActiveStatus("server ready")
        """
    )
    return {"any_charm.py": any_charm_py}


@pytest.fixture(scope="module", name="any_charm_src_invalid_port")
def any_charm_src_invalid_port_fixture() -> dict[str, str]:
    """Any-charm configuration to test with haproxy (invalid port)."""
    any_charm_py = textwrap.dedent(
        """\
        import ops
        from any_charm_base import AnyCharmBase
        import textwrap

        relation_data = textwrap.dedent(
            \"\"\"
                - service_name: my_web_app
                  service_host: 0.0.0.0
                  service_port: 80000
                  service_options:
                  - mode http
                  - timeout client 300000
                  - timeout server 300000
                  - balance leastconn
                  - option httpchk HEAD / HTTP/1.0
                  - acl server1 path_beg -i /server1/health
                  - use_backend server1 if server1
                  servers:
                  - - default
                    - 10.0.0.1
                    - 80000
                    - check
            \"\"\"
        )

        class AnyCharm(AnyCharmBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)


            def update_relation_data(self):
                relation = self.model.get_relation("provide-http")
                relation.data[self.unit].update(
                    {
                        "services": relation_data,
                        "hostname": "", "port": ""
                    }
                )
        """
    )
    return {"any_charm.py": any_charm_py}


@pytest.fixture(scope="module", name="any_charm_ingress_requirer_name")
def any_charm_ingress_requirer_name_fixture() -> str:
    """Name of the ingress requirer charm."""
    return "any-charm-ingress-requirer"


@pytest.fixture(scope="module", name="any_charm_src_ingress_requirer")
def any_charm_src_ingress_requirer_fixture() -> dict[str, str]:
    """Any charm ingress requirer source code fixture."""
    any_charm_py = textwrap.dedent(
        """\
    import pathlib
    import subprocess
    import ops
    from any_charm_base import AnyCharmBase
    from ingress import IngressPerAppRequirer
    import apt

    class AnyCharm(AnyCharmBase):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.ingress = IngressPerAppRequirer(self, port=80, strip_prefix=True)

        def start_server(self):
            apt.update()
            apt.add_package(package_names="apache2")
            www_dir = pathlib.Path("/var/www/html")
            file_path = www_dir / "ok"
            file_path.parent.mkdir(exist_ok=True)
            file_path.write_text("ok!")
            self.unit.status = ops.ActiveStatus("Server ready")
    """
    )

    return {
        "ingress.py": pathlib.Path("lib/charms/traefik_k8s/v2/ingress.py").read_text(
            encoding="utf-8"
        ),
        "apt.py": pathlib.Path("lib/charms/operator_libs_linux/v0/apt.py").read_text(
            encoding="utf-8"
        ),
        "any_charm.py": any_charm_py,
    }


@pytest.fixture(name="any_charm_ingress_requirer")
def any_charm_ingress_requirer_fixture(
    pytestconfig: pytest.Config,
    juju: jubilant.Juju,
    any_charm_src_ingress_requirer: dict[str, str],
    any_charm_ingress_requirer_name: str,
) -> str:
    """Deploy any-charm configured as a requirer for the ingress-per-app interface.

    Args:
        pytestconfig: Pytest configuration.
        juju: Jubilant juju fixture.
        any_charm_src_ingress_requirer: Source overwrite for any-charm.
        any_charm_ingress_requirer_name: App name.

    Returns:
        The any-charm ingress requirer app name.
    """
    if (
        pytestconfig.getoption("--no-deploy")
        and any_charm_ingress_requirer_name in juju.status().apps
    ):
        logger.warning("Using existing application: %s", any_charm_ingress_requirer_name)
        return any_charm_ingress_requirer_name
    # Write large src-overwrite to a file to avoid ARG_MAX CLI limit
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(json.dumps(any_charm_src_ingress_requirer).encode("utf-8"))
        tf.flush()
        juju.deploy(
            "any-charm",
            app=any_charm_ingress_requirer_name,
            channel="beta",
            config={
                "src-overwrite": f"@{tf.name}",
                "python-packages": "pydantic<2.0",
            },
        )
    juju.wait(lambda status: jubilant.all_active(status, any_charm_ingress_requirer_name))
    juju.run(f"{any_charm_ingress_requirer_name}/0", "rpc", {"method": "start_server"})
    return any_charm_ingress_requirer_name


@pytest.fixture(name="any_charm_requirer")
def any_charm_requirer_fixture(juju: jubilant.Juju, any_charm_src: dict[str, str]) -> str:
    """Deploy any-charm configured as a requirer for the reverseproxy relation.

    Args:
        juju: Jubilant juju fixture.
        any_charm_src: Source overwrite for any-charm.

    Returns:
        The any-charm requirer app name.
    """
    app_name = "requirer"
    juju.deploy(
        "any-charm",
        app=app_name,
        channel="beta",
        config={"src-overwrite": json.dumps(any_charm_src)},
    )
    juju.wait(lambda status: jubilant.all_active(status, app_name))
    return app_name


@pytest.fixture(name="reverseproxy_requirer")
def reverseproxy_requirer_fixture(
    juju: jubilant.Juju,
) -> str:
    """Deploy haproxy from channel as a requirer for the website relation.

    Args:
        juju: Jubilant juju fixture.

    Returns:
        The reverseproxy-requirer app name.
    """
    app_name = "reverseproxy-requirer"
    juju.deploy(
        "haproxy",
        app=app_name,
        channel="latest/edge",
    )
    juju.wait(lambda status: jubilant.all_active(status, app_name))
    return app_name


@pytest.fixture(name="hacluster")
def hacluster_fixture(
    juju: jubilant.Juju,
) -> str:
    """Deploy hacluster.

    Args:
        juju: Jubilant juju fixture.

    Returns:
        The hacluster app name.
    """
    app_name = "hacluster"
    juju.deploy(
        "hacluster",
        app=app_name,
        channel="2.4/edge",
        base="ubuntu@24.04",
    )
    juju.wait(
        lambda status: app_name in status.apps,
    )
    return app_name


@pytest.fixture(name="haproxy_route_requirer")
def haproxy_route_requirer_fixture(juju: jubilant.Juju) -> str:
    """Deploy any-charm configured as a requirer for the haproxy-route interface.

    Args:
        juju: Jubilant juju fixture.

    Returns:
        The haproxy-route-requirer app name.
    """
    app_name = "haproxy-route-requirer"
    src_overwrite = json.dumps(
        {
            "any_charm.py": pathlib.Path(HAPROXY_ROUTE_REQUIRER_SRC).read_text(encoding="utf-8"),
            "haproxy_route.py": pathlib.Path(HAPROXY_ROUTE_LIB_SRC).read_text(encoding="utf-8"),
            "apt.py": pathlib.Path(APT_LIB_SRC).read_text(encoding="utf-8"),
        }
    )
    # Write large src-overwrite to a file to avoid ARG_MAX CLI limit
    with tempfile.NamedTemporaryFile(dir=".") as tf:
        tf.write(src_overwrite.encode("utf-8"))
        tf.flush()
        juju.deploy(
            "any-charm",
            channel="beta",
            app=app_name,
            config={
                "src-overwrite": f"@{tf.name}",
                "python-packages": "pydantic~=2.10\nvalidators",
            },
        )
    juju.wait(lambda status: jubilant.all_active(status, app_name))
    juju.run(f"{app_name}/0", "rpc", {"method": "start_server"})
    return app_name


class DNSResolverHTTPSAdapter(HTTPAdapter):
    """A simple mounted DNS resolver for HTTP requests."""

    def __init__(
        self,
        hostname,
        ip,
    ):
        """Initialize the dns resolver.

        Args:
            hostname: DNS entry to resolve.
            ip: Target IP address.
        """
        self.hostname = hostname
        self.ip = ip
        super().__init__(
            pool_connections=DEFAULT_POOLSIZE,
            pool_maxsize=DEFAULT_POOLSIZE,
            max_retries=DEFAULT_RETRIES,
            pool_block=DEFAULT_POOLBLOCK,
        )

    # Ignore pylint rule as this is the parent method signature
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """Wrap HTTPAdapter send to modify the outbound request.

        Args:
            request: Outbound HTTP request.
            stream: argument used by parent method.
            timeout: argument used by parent method.
            verify: argument used by parent method.
            cert: argument used by parent method.
            proxies: argument used by parent method.

        Returns:
            Response: HTTP response after modification.
        """
        connection_pool_kwargs = self.poolmanager.connection_pool_kw

        result = urlparse(request.url)
        if result.hostname == self.hostname:
            ip = self.ip
            if result.scheme == "https" and ip:
                request.url = request.url.replace(
                    "https://" + result.hostname,
                    "https://" + ip,
                )
                connection_pool_kwargs["server_hostname"] = result.hostname
                connection_pool_kwargs["assert_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            else:
                connection_pool_kwargs.pop("server_hostname", None)
                connection_pool_kwargs.pop("assert_hostname", None)

        return super().send(request, stream, timeout, verify, cert, proxies)
