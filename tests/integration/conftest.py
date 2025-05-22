# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for integration tests."""

import ipaddress
import json
import logging
import os.path
import pathlib
import textwrap
import typing

import pytest
import pytest_asyncio
from juju.application import Application
from juju.client._definitions import FullStatus, UnitStatus
from juju.model import Model
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
GATEWAY_CLASS_CONFIG = "cilium"
HAPROXY_ROUTE_REQUIRER_SRC = "tests/integration/haproxy_route_requirer.py"
HAPROXY_ROUTE_LIB_SRC = "lib/charms/haproxy/v0/haproxy_route.py"
APT_LIB_SRC = "lib/charms/operator_libs_linux/v0/apt.py"


@pytest_asyncio.fixture(scope="module", name="model")
async def model_fixture(ops_test: OpsTest) -> Model:
    """The current test model."""
    assert ops_test.model
    return ops_test.model


@pytest_asyncio.fixture(scope="module", name="charm")
async def charm_fixture(pytestconfig: pytest.Config) -> str:
    """Get value from parameter charm-file."""
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    if not os.path.exists(charm):
        logger.info("Using parent directory for charm file")
        charm = os.path.join("..", charm)
    return charm


@pytest_asyncio.fixture(scope="module", name="application")
async def application_fixture(
    charm: str, model: Model
) -> typing.AsyncGenerator[Application, None]:
    """Deploy the charm."""
    # Deploy the charm and wait for active/idle status
    application = await model.deploy(f"./{charm}", trust=True)
    await model.wait_for_idle(
        apps=[application.name],
        status="active",
        raise_on_error=True,
    )
    yield application


@pytest_asyncio.fixture(scope="module", name="certificate_provider_application")
async def certificate_provider_application_fixture(
    model: Model,
) -> Application:
    """Deploy self-signed-certificates."""
    application = await model.deploy("self-signed-certificates", channel="1/edge")
    await model.wait_for_idle(apps=[application.name], status="active")
    return application


@pytest_asyncio.fixture(scope="module", name="configured_application_with_tls")
async def configured_application_with_tls_fixture(
    application: Application,
    certificate_provider_application: Application,
):
    """The haproxy charm configured and integrated with tls provider."""
    await application.set_config({"external-hostname": TEST_EXTERNAL_HOSTNAME_CONFIG})
    await application.model.add_relation(application.name, certificate_provider_application.name)
    await application.model.wait_for_idle(
        apps=[certificate_provider_application.name, application.name],
        idle_period=30,
        status="active",
    )
    return application


async def get_unit_ip_address(
    application: Application,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Get the unit address to make HTTP requests.

    Args:
        application: The deployed application

    Returns:
        The unit address
    """
    status: FullStatus = await application.model.get_status([application.name])
    application = typing.cast(Application, status.applications[application.name])
    unit_status: UnitStatus = next(iter(application.units.values()))
    assert unit_status.public_address, "Invalid unit address"
    address = (
        unit_status.public_address
        if isinstance(unit_status.public_address, str)
        else unit_status.public_address.decode()
    )

    return ipaddress.ip_address(address)


async def get_unit_address(application: Application) -> str:
    """Get the unit address to make HTTP requests.

    Args:
        application: The deployed application

    Returns:
        The unit address
    """
    unit_ip_address = await get_unit_ip_address(application)
    url = f"http://{str(unit_ip_address)}"
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        url = f"http://[{str(unit_ip_address)}]"
    return url


@pytest_asyncio.fixture(scope="module", name="any_charm_src")
async def any_charm_src_fixture() -> dict[str, str]:
    """any-charm configuration to test with haproxy."""
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


@pytest_asyncio.fixture(scope="module", name="any_charm_src_invalid_port")
async def any_charm_src_invalid_port_fixture() -> dict[str, str]:
    """any-charm configuration to test with haproxy."""
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


@pytest_asyncio.fixture(scope="module", name="any_charm_ingress_requirer_name")
async def any_charm_ingress_requirer_name_fixture() -> str:
    """Name of the ingress requirer charm."""
    return "any-charm-ingress-requirer"


@pytest_asyncio.fixture(scope="module", name="any_charm_src_ingress_requirer")
async def any_charm_src_ingress_requirer_fixture() -> dict[str, str]:
    """
    assert: None
    action: Build and deploy nginx-ingress-integrator charm, also deploy and relate an any-charm
        application with ingress relation for test purposes.
    assert: HTTP request should be forwarded to the application.
    """
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


@pytest_asyncio.fixture(scope="function", name="any_charm_ingress_requirer")
async def any_charm_ingress_requirer_fixture(
    model: Model,
    any_charm_src_ingress_requirer: dict[str, str],
    any_charm_ingress_requirer_name: str,
) -> typing.AsyncGenerator[Application, None]:
    """Deploy any-charm and configure it to serve as a requirer for the http interface."""
    application = await model.deploy(
        "any-charm",
        application_name=any_charm_ingress_requirer_name,
        channel="beta",
        config={
            "src-overwrite": json.dumps(any_charm_src_ingress_requirer),
            "python-packages": "pydantic<2.0",
        },
    )
    await model.wait_for_idle(apps=[application.name], status="active")
    action = await application.units[0].run_action("rpc", method="start_server")
    await action.wait()
    yield application


@pytest_asyncio.fixture(scope="function", name="any_charm_requirer")
async def any_charm_requirer_fixture(
    model: Model, any_charm_src: dict[str, str]
) -> typing.AsyncGenerator[Application, None]:
    """Deploy any-charm and configure it to serve as a requirer for the http interface."""
    application = await model.deploy(
        "any-charm",
        application_name="requirer",
        channel="beta",
        config={"src-overwrite": json.dumps(any_charm_src)},
    )
    await model.wait_for_idle(apps=[application.name], status="active")
    yield application


@pytest_asyncio.fixture(scope="function", name="reverseproxy_requirer")
async def reverseproxy_requirer_fixture(
    model: Model,
) -> typing.AsyncGenerator[Application, None]:
    """Deploy any-charm and configure it to serve as a requirer for the http interface."""
    application = await model.deploy(
        "haproxy",
        application_name="reverseproxy-requirer",
        channel="latest/edge",
    )
    await model.wait_for_idle(apps=[application.name], status="active")
    yield application


@pytest_asyncio.fixture(scope="function", name="hacluster")
async def hacluster_fixture(
    model: Model,
) -> typing.AsyncGenerator[Application, None]:
    """Deploy hacluster."""
    application = await model.deploy(
        "hacluster", application_name="hacluster", channel="2.4/edge", series="noble"
    )
    await model.wait_for_idle(apps=[application.name], wait_for_at_least_units=0, status="unknown")
    yield application


@pytest_asyncio.fixture(scope="function", name="haproxy_route_requirer")
async def haproxy_route_requirer_fixture(model: Model) -> typing.AsyncGenerator[Application, None]:
    """Deploy any-charm and configure it to serve as a requirer for the http interface."""
    application = await model.deploy(
        "any-charm",
        channel="beta",
        application_name="haproxy-route-requirer",
        config={
            "src-overwrite": json.dumps(
                {
                    "any_charm.py": pathlib.Path(HAPROXY_ROUTE_REQUIRER_SRC).read_text(
                        encoding="utf-8"
                    ),
                    "haproxy_route.py": pathlib.Path(HAPROXY_ROUTE_LIB_SRC).read_text(
                        encoding="utf-8"
                    ),
                    "apt.py": pathlib.Path(APT_LIB_SRC).read_text(encoding="utf-8"),
                }
            ),
            "python-packages": "pydantic",
        },
    )
    await model.wait_for_idle(apps=[application.name], status="active")

    action = await application.units[0].run_action("rpc", method="start_server")
    await action.wait()
    yield application
