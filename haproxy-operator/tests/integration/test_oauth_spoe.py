# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for haproxy spoe auth."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="iam_bundle")
def deploy_iam_bundle_fixture(juju: jubilant.Juju):
    """Deploy Canonical identity bundle."""
    # https://github.com/canonical/iam-bundle-integration

    if juju.status().apps.get("hydra"):
        logger.info("identity-platform is already deployed")
        return


@pytest.mark.abort_on_fail
def test_oauth_spoe(juju: jubilant.Juju, iam_bundle):
    assert False
