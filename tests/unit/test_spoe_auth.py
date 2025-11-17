# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for SPOE authentication state."""

from unittest.mock import MagicMock

from state.spoe_auth import SPOE_AUTH_RELATION, SpoeAuthInformation


def test_spoe_auth_information_no_relation():
    """Test SpoeAuthInformation when no relation exists."""
    charm = MagicMock()
    charm.model.get_relation.return_value = None

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert spoe_info.agent_address is None
    assert spoe_info.agent_port is None


def test_spoe_auth_information_with_relation_no_data():
    """Test SpoeAuthInformation when relation exists but has no data."""
    charm = MagicMock()
    relation = MagicMock()
    relation.units = []
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert spoe_info.agent_address is None
    assert spoe_info.agent_port is None


def test_spoe_auth_information_with_valid_data():
    """Test SpoeAuthInformation when relation has valid data."""
    charm = MagicMock()
    relation = MagicMock()
    unit = MagicMock()
    relation.units = [unit]
    relation.data = {unit: {"agent-address": "10.0.0.1", "agent-port": "9000"}}
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is True
    assert spoe_info.agent_address == "10.0.0.1"
    assert spoe_info.agent_port == 9000


def test_spoe_auth_information_with_invalid_port():
    """Test SpoeAuthInformation when port is invalid."""
    charm = MagicMock()
    relation = MagicMock()
    unit = MagicMock()
    relation.units = [unit]
    relation.data = {unit: {"agent-address": "10.0.0.1", "agent-port": "invalid"}}
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert spoe_info.agent_address is None
    assert spoe_info.agent_port is None


def test_spoe_auth_information_with_partial_data():
    """Test SpoeAuthInformation when only address is provided."""
    charm = MagicMock()
    relation = MagicMock()
    unit = MagicMock()
    relation.units = [unit]
    relation.data = {unit: {"agent-address": "10.0.0.1"}}
    charm.model.get_relation.return_value = relation

    spoe_info = SpoeAuthInformation.from_charm(charm)
    assert spoe_info.enabled is False
    assert spoe_info.agent_address is None
    assert spoe_info.agent_port is None

