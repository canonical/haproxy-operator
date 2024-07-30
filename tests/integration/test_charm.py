# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for haproxy charm."""
import pytest
from juju.application import Application


@pytest.mark.abort_on_fail
async def test_deploy(application: Application):
    """Deploy the charm."""
    assert application
