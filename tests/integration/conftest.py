# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""General configuration module for integration tests."""

import logging
import os.path
import typing
from pathlib import Path

import pytest
import pytest_asyncio
import yaml
from juju.application import Application
from juju.model import Model
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

TEST_EXTERNAL_HOSTNAME_CONFIG = "haproxy.internal"
GATEWAY_CLASS_CONFIG = "cilium"


@pytest.fixture(scope="module", name="metadata")
def metadata_fixture():
    """Provide charm metadata."""
    return yaml.safe_load(Path("./charmcraft.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module", name="app_name")
def app_name_fixture(metadata):
    """Provide app name from the metadata."""
    return metadata["name"]


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


@pytest_asyncio.fixture(scope="function", name="get_unit_ip_list")
async def get_unit_ip_list_fixture(ops_test: OpsTest, app_name: str):
    """Retrieve unit ip addresses, similar to fixture_get_unit_status_list."""

    async def get_unit_ip_list_action():
        """Extract the IPs from juju units.

        Returns:
            A list of IPs of the juju units in the model.
        """
        model = typing.cast(Model, ops_test.model)  # typing.cast used for mypy
        status = await model.get_status()
        units = status.applications[app_name].units
        ip_list = [
            units[key].address for key in sorted(units.keys(), key=lambda n: int(n.split("/")[-1]))
        ]
        return ip_list

    yield get_unit_ip_list_action


@pytest_asyncio.fixture(scope="function")
async def unit_ip_list(get_unit_ip_list):
    """Yield ip addresses of current units."""
    yield await get_unit_ip_list()


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
