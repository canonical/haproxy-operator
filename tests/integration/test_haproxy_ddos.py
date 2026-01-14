# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for HAProxy DDoS protection functionality."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)


def test_haproxy_ddos_protection_integration(
    lxd_juju, application, ddos_protection_configurator
):
    """Test that HAProxy integrates correctly with DDoS protection configurator."""
    lxd_juju.integrate(
        f"{ddos_protection_configurator}:ddos-protection",
        f"{application}:ddos-protection",
    )

    lxd_juju.wait(jubilant.all_active)
