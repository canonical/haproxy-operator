# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for integration tests."""

import ipaddress
import logging
import os.path
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
