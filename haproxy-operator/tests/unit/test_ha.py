# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the HA state component."""

from unittest.mock import MagicMock

import pytest

from state.ha import (
    HACLUSTER_INTEGRATION,
    HAPROXY_PEER_INTEGRATION,
    HAInformation,
    HAInformationValidationError,
)


def _build_charm(
    config: dict[str, str],
    ha_relation: MagicMock | None,
    peer_relation: MagicMock | None = None,
) -> MagicMock:
    """Build a minimal charm mock exposing the configured HA relations."""
    charm = MagicMock()
    charm.config = config
    charm.model.get_relation.side_effect = lambda name: {
        HACLUSTER_INTEGRATION: ha_relation,
        HAPROXY_PEER_INTEGRATION: peer_relation,
    }.get(name)
    return charm


def test_ha_information():
    """
    arrange: Given a charm with ha integration enabled and a valid vip config.
    act: Initialize HAInformation state component.
    assert: State component is correctly generated.
    """
    mock_vip = "10.0.0.1"
    ha_relation = MagicMock()
    ha_relation.units = [MagicMock()]
    charm = _build_charm({"vip": mock_vip}, ha_relation)

    ha_information = HAInformation.from_charm(charm)

    assert str(ha_information.vip) == mock_vip
    assert ha_information.ha_integration_ready


def test_ha_information_vip_invalid():
    """
    arrange: Given a charm with ha integration enabled and an invalid vip config.
    act: Initialize HAInformation state component.
    assert: HAInformationValidationError is raised.
    """
    ha_relation = MagicMock()
    ha_relation.units = [MagicMock()]
    charm = _build_charm({"vip": "invalid"}, ha_relation)

    with pytest.raises(HAInformationValidationError):
        HAInformation.from_charm(charm)


def test_ha_information_vip_integration_not_ready():
    """
    arrange: Given a charm with ha integration missing.
    act: Initialize HAInformation state component.
    assert: ha_integration_ready is False and vip is None.
    """
    charm = _build_charm({}, None)

    ha_information = HAInformation.from_charm(charm)

    assert not ha_information.ha_integration_ready
    assert ha_information.vip is None
