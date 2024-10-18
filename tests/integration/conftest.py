# Copyright 2024 Canonical Ltd.
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
    application = await model.deploy("self-signed-certificates", channel="edge")
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


async def get_unit_address(application: Application) -> str:
    """Get the unit address to make HTTP requests.

    Args:
        application: The deployed application

    Returns:
        The unit address
    """
    status: FullStatus = await application.model.get_status([application.name])
    unit_status: UnitStatus = next(iter(status.applications[application.name].units.values()))
    assert unit_status.public_address, "Invalid unit address"
    address = (
        unit_status.public_address
        if isinstance(unit_status.public_address, str)
        else unit_status.public_address.decode()
    )

    unit_ip_address = ipaddress.ip_address(address)
    url = f"http://{str(unit_ip_address)}"
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        url = f"http://[{str(unit_ip_address)}]"
    return url


@pytest_asyncio.fixture(scope="module", name="any_charm_src")
async def any_charm_src_fixture() -> dict[str, str]:
    """any-charm configuration to test with haproxy."""
    return {
        "any_charm.py": textwrap.dedent(
            """
        from any_charm_base import AnyCharmBase
        import textwrap
        import logging
        logger = logging.getLogger()
        relation_data = textwrap.dedent(
            \"\"\"
                - service_name: my_web_app
                  service_host: 0.0.0.0
                  service_port: 80
                  service_options:
                  - mode http
                  - timeout client 300000
                  - timeout server 300000
                  - balance leastconn
                  - option httpchk HEAD / HTTP/1.0
                  - acl service_1 path_beg -i /service_1
                  - use_backend extra_service_1 if service_1
                  servers: [[server1, 10.0.1.1, 80, [check, rise 2, fall 5, maxconn 50]]]
                  backends:
                  - backend_name: extra_service_1
                    servers:
                    - - extra_server_1
                      - 10.0.1.1
                      - 8000
                      - &id001
                        - check
                        - inter 5000
                        - rise 2
                        - fall 5
                        - maxconn 50
                    - - extra_server_2
                      - 10.0.1.2
                      - 8001
                      - *id001
            \"\"\"
        )
        class AnyCharm(AnyCharmBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def update_relation_data(self):
                relation = self.model.get_relation("provide-http")
                relation.data[self.unit].update(
                    {"services": relation_data, "hostname": "", "port": ""}
                )

            def update_relation_data_single_service(self):
                relation = self.model.get_relation("provide-http")
                relation.data[self.unit].update(
                    {"hostname": "10.0.0.0", "port": "80", "services": ""}
                )
        """
        ),
    }


@pytest_asyncio.fixture(scope="module", name="any_charm_ingress_requirer_name")
async def any_charm_ingress_requirer_name_fixture() -> str:
    """Name of the ingress requirer charm."""
    return "any-charm-ingress-requirer"


@pytest_asyncio.fixture(scope="module", name="any_charm_src_ingress_requirer")
async def any_charm_src_ingress_requirer_fixture(
    model: Model, any_charm_ingress_requirer_name: str
) -> dict[str, str]:
    """
    assert: None
    action: Build and deploy nginx-ingress-integrator charm, also deploy and relate an any-charm
        application with ingress relation for test purposes.
    assert: HTTP request should be forwarded to the application.
    """
    ingress_path_prefix = f"{model.name}-{any_charm_ingress_requirer_name}"
    any_charm_py = textwrap.dedent(
        f"""\
    import pathlib
    import subprocess
    import ops
    from any_charm_base import AnyCharmBase
    from ingress import IngressPerAppRequirer
    import apt

    class AnyCharm(AnyCharmBase):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.ingress = IngressPerAppRequirer(self, port=80)

        def start_server(self):
            apt.update()
            apt.add_package(package_names="apache2")
            www_dir = pathlib.Path("/var/www/html")
            file_path = www_dir / "{ingress_path_prefix}" / "ok"
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
