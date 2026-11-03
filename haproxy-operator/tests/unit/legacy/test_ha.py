# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for ha."""

import pytest
from ops.testing import Harness

from state.ha import HACLUSTER_INTEGRATION, HAInformation, HAInformationValidationError

# These legacy tests still use Harness, which ops marks as deprecated with a
# PendingDeprecationWarning. The unit suite runs with warnings promoted to
# errors (see pyproject.toml), so ignore that one warning here until the tests
# are ported to ops.testing.Context like the rest of tests/unit.
pytestmark = pytest.mark.filterwarnings("ignore:Harness is deprecated:PendingDeprecationWarning")


def test_ha_information(harness: Harness):
    """
    arrange: Given a charm with ha integration enabled and a valid vip config.
    act: Initialize HAInformation state component.
    assert: State component is correctly generated.
    """
    mock_vip = "10.0.0.1"
    harness.add_relation(HACLUSTER_INTEGRATION, "hacluster", unit_data={})
    harness.update_config({"vip": mock_vip})
    harness.begin()
    ha_information = HAInformation.from_charm(harness.charm)
    assert str(ha_information.vip) == mock_vip
    assert ha_information.ha_integration_ready


def test_ha_information_vip_invalid(harness: Harness):
    """
    arrange: Given a charm with ha integration enabled and an invalid vip config.
    act: Initialize HAInformation state component.
    assert: HAInformationValidationError is raised.
    """
    mock_vip = "invalid"
    harness.add_relation(HACLUSTER_INTEGRATION, "hacluster")
    harness.update_config({"vip": mock_vip})
    harness.begin()
    with pytest.raises(HAInformationValidationError):
        HAInformation.from_charm(harness.charm)


def test_ha_information_vip_integration_not_ready(harness: Harness):
    """
    arrange: Given a charm with ha integration missing.
    act: Initialize HAInformation state component.
    assert: ha_integration_ready is False and vip is None.
    """
    harness.begin()
    ha_information = HAInformation.from_charm(harness.charm)
    assert not ha_information.ha_integration_ready
    assert ha_information.vip is None
