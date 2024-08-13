# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm file."""

from unittest.mock import MagicMock

import pytest
from ops.model import SecretNotFoundError, Secret
from ops.testing import Harness

from state.tls import TLSInformation, TLSNotReadyError
from tls_relation import TLSRelationService

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG


def test_tls_information_integration_missing(harness: Harness):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSNotReadyError is raised.
    """
    harness.begin()
    with pytest.raises(TLSNotReadyError):
        TLSInformation.from_charm(harness.charm, harness.charm.certificates)


def test_generate_private_key(
    harness_with_mock_certificates_integration: Harness, juju_secret_mock: MagicMock
):
    """
    arrange: Given a haproxy charm with mock juju secret and certificates integration.
    act: run generate private_key method.
    assert: set_content is called.
    """
    harness = harness_with_mock_certificates_integration
    harness.begin()

    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    tls_relation.generate_private_key(TEST_EXTERNAL_HOSTNAME_CONFIG)

    juju_secret_mock.set_content.assert_called_once()


def test_generate_private_key_assertion_error(harness: Harness):
    """
    arrange: Given a haproxy charm with missing certificates integration.
    act: run generate private_key method.
    assert: AssertionError is raised
    """
    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    with pytest.raises(AssertionError):
        tls_relation.generate_private_key(TEST_EXTERNAL_HOSTNAME_CONFIG)


def test_generate_private_key_secret_not_found(
    harness_with_mock_certificates_integration: Harness, monkeypatch: pytest.MonkeyPatch
):
    """
    arrange: Given a haproxy charm with missing certificates integration.
    act: run generate private_key method.
    assert: AssertionError is raised
    """
    monkeypatch.setattr("ops.model.Model.get_secret", MagicMock(side_effect=SecretNotFoundError))
    created_secret_mock = MagicMock(spec=Secret)
    harness = harness_with_mock_certificates_integration

    harness.begin()
    tls_relation = TLSRelationService(harness.model, harness.charm.certificates)
    # monkeypatch.setattr(
    #     "tls_relation.application.add_secret",
    #     MagicMock(return_value=created_secret_mock),
    # )
    tls_relation.application = MagicMock(return_value=created_secret_mock)
    tls_relation.generate_private_key(TEST_EXTERNAL_HOSTNAME_CONFIG)
    created_secret_mock.grant.assert_called_once()
