# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns_record service module."""

from unittest.mock import MagicMock

import pytest
from charms.dns_record.v0.dns_record import (
    CreateRecordRequestError,
    DNSRecordRequires,
    RecordRequest,
)

from dns_record import DNSRecordService


@pytest.fixture(name="mock_requirer")
def mock_requirer_fixture():
    """Create a mocked DNSRecordRequires."""
    mock = MagicMock(spec=DNSRecordRequires)
    mock.relation_name = "dns-record"
    return mock


@pytest.fixture(name="mock_model")
def mock_model_fixture():
    """Create a mocked ops.Model with a dns-record relation."""
    model = MagicMock()
    model.get_relation.return_value = MagicMock()
    return model


@pytest.fixture(name="service")
def service_fixture(mock_model, mock_requirer):
    """Create a DNSRecordService with mocked dependencies."""
    return DNSRecordService(mock_model, mock_requirer)


def test_update_dns_records_calls_create_and_update(service, mock_requirer):
    """
    arrange: service with one hostname and a valid IP
    act: call update_dns_records
    assert: create_record_request and update_relation_data are called correctly
    """
    fake_entry = MagicMock(spec=RecordRequest)
    mock_requirer.create_record_request.return_value = fake_entry

    service.update_dns_records(["app.example.com"], "10.0.0.5")

    mock_requirer.create_record_request.assert_called_once_with(
        "@ app.example.com 600 IN A 10.0.0.5"
    )
    mock_requirer.update_relation_data.assert_called_once_with([fake_entry])


def test_update_dns_records_multiple_hostnames(service, mock_requirer):
    """
    arrange: service with multiple hostnames
    act: call update_dns_records
    assert: one RecordRequest is created per hostname
    """
    fake_entry = MagicMock(spec=RecordRequest)
    mock_requirer.create_record_request.return_value = fake_entry

    service.update_dns_records(["a.example.com", "b.example.com"], "10.0.0.5")

    assert mock_requirer.create_record_request.call_count == 2
    mock_requirer.create_record_request.assert_any_call("@ a.example.com 600 IN A 10.0.0.5")
    mock_requirer.create_record_request.assert_any_call("@ b.example.com 600 IN A 10.0.0.5")
    mock_requirer.update_relation_data.assert_called_once_with([fake_entry, fake_entry])


@pytest.mark.parametrize(
    "hostnames, ip, has_relation",
    [
        pytest.param(["app.example.com"], "10.0.0.5", False, id="no_relation"),
        pytest.param([], "10.0.0.5", True, id="empty_hostnames"),
        pytest.param(["app.example.com"], "", True, id="empty_ip"),
    ],
)
def test_update_dns_records_noop(hostnames, ip, has_relation, mock_model, mock_requirer):
    """
    arrange: conditions where update should be a no-op (no relation, empty hostnames, empty IP)
    act: call update_dns_records
    assert: update_relation_data is never called
    """
    if not has_relation:
        mock_model.get_relation.return_value = None
    service = DNSRecordService(mock_model, mock_requirer)

    service.update_dns_records(hostnames, ip)

    mock_requirer.update_relation_data.assert_not_called()


def test_update_dns_records_skips_invalid_hostname(service, mock_requirer):
    """
    arrange: one valid and one invalid hostname
    act: call update_dns_records
    assert: only the valid hostname's record is published
    """
    valid_entry = MagicMock(spec=RecordRequest)
    mock_requirer.create_record_request.side_effect = [
        CreateRecordRequestError("bad"),
        valid_entry,
    ]

    service.update_dns_records(["invalid!", "good.example.com"], "10.0.0.5")

    mock_requirer.update_relation_data.assert_called_once_with([valid_entry])
