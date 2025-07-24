# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the states of different modes."""

from unittest.mock import Mock

import pytest
from charms import traefik_k8s

from state.ingress import IngressIntegrationDataValidationError, IngressRequirersInformation
from state.ingress_per_unit import (
    HAProxyBackend,
    IngressPerUnitIntegrationDataValidationError,
    IngressPerUnitRequirersInformation,
)


def test_ingress_per_unit_from_provider():
    """
    arrange: Setup a mock provider with the required unit data.
    act: Initialize the IngressPerUnitRequirersInformation.
    assert: The state component is initialized correctly with expected data.
    """
    unit_data = {
        "requirer/0": ("juju-unit1.lxd", 8080, True),
        "requirer/1": ("juju-unit2.lxd", 8081, False),
    }

    units = []
    for unit_name in unit_data:
        unit = Mock()
        unit.name = unit_name
        units.append(unit)

    provider = Mock()
    provider.relations = [Mock(units=units)]
    provider.get_data.side_effect = lambda rel, unit: {
        "name": unit.name,
        "model": "test-model",
        "host": unit_data[unit.name][0],
        "port": unit_data[unit.name][1],
        "strip-prefix": unit_data[unit.name][2],
    }

    result = IngressPerUnitRequirersInformation.from_provider(provider)

    expected = [
        HAProxyBackend(
            backend_name="test-model_requirer_0",
            backend_path="test-model-requirer/0",
            hostname_or_ip="juju-unit1.lxd",
            port=8080,
            strip_prefix=True,
        ),
        HAProxyBackend(
            backend_name="test-model_requirer_1",
            backend_path="test-model-requirer/1",
            hostname_or_ip="juju-unit2.lxd",
            port=8081,
            strip_prefix=False,
        ),
    ]
    assert result.backends == expected


def test_ingress_per_unit_from_provider_validation_error():
    """
    arrange: Setup ingress-per-unit provider mock with invalid data.
    act: Initialize the IngressPerUnitRequirersInformation.
    assert: IngressPerUnitIntegrationDataValidationError is raised.
    """
    provider = Mock(relations=[Mock(units=[Mock(name="requirer-charm/0")])])

    provider.get_data.side_effect = traefik_k8s.v1.ingress_per_unit.DataValidationError()

    with pytest.raises(IngressPerUnitIntegrationDataValidationError):
        IngressPerUnitRequirersInformation.from_provider(provider)


def test_ingress_from_provider_validation_error():
    """
    arrange: Setup ingress provider mock with invalid data.
    act: Initialize the IngressRequirersInformation.
    assert: IngressIntegrationDataValidationError is raised.
    """
    provider = Mock(relations=[Mock(units=[Mock(name="requirer-charm/0")])])

    provider.get_data.side_effect = traefik_k8s.v2.ingress.DataValidationError()

    with pytest.raises(IngressIntegrationDataValidationError):
        IngressRequirersInformation.from_provider(provider)
