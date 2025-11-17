# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit test fixtures for haproxy-spoe-auth-operator."""

from unittest.mock import patch

import pytest
from ops.testing import Context

from charm import HaproxySpoeAuthCharm


@pytest.fixture(name="context_with_install_mock")
def context_with_install_mock_fixture():
    """Context relation fixture.

    Yield: The modeled haproxy-peers relation.
    """
    with (
        patch(
            "haproxy_spoe_auth_operator.src.haproxy_spoe_auth_service.SpoeAuthService.install"
        ) as install_mock,
    ):
        yield (
            Context(
                charm_type=HaproxySpoeAuthCharm,
            ),
            (install_mock,),
        )
