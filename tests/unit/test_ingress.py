# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy charm ingress."""

import pytest
from ops.testing import Harness

from state.ingress import (
    HAProxyBackend,
    HAProxyServer,
    IngressIntegrationDataValidationError,
    IngressRequirersInformation,
)


def test_ingress_information_from_charm(
    harness: Harness,
    ingress_requirer_application_data: dict[str, str],
    ingress_requirer_unit_data: dict[str, str],
):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSNotReadyError is raised.
    """
    harness.begin()
    harness.add_relation(
        "ingress",
        "requirer-charm",
        app_data=ingress_requirer_application_data,
        unit_data=ingress_requirer_unit_data,
    )
    # We disable protected-access since we want to test the ingress provider
    ingress_information = IngressRequirersInformation.from_provider(
        harness.charm._ingress_provider  # pylint: disable=protected-access
    )
    assert ingress_information.backends == [
        HAProxyBackend(
            backend_name="testing-ingress_requirer",
            servers=[
                HAProxyServer(
                    server_name="testing-ingress_requirer-0", hostname_or_ip="10.0.0.1", port=8080
                )
            ],
        )
    ]


def test_ingress_information_from_charm_data_validation_error(
    harness: Harness,
    ingress_requirer_application_data: dict[str, str],
):
    """
    arrange: Given a charm with tls integration missing.
    act: Initialize TLSInformation state component.
    assert: TLSNotReadyError is raised.
    """
    harness.begin()
    harness.add_relation(
        "ingress",
        "requirer-charm",
        app_data=ingress_requirer_application_data,
    )
    with pytest.raises(IngressIntegrationDataValidationError):
        # We disable protected-access since we want to test the ingress provider
        IngressRequirersInformation.from_provider(
            harness.charm._ingress_provider  # pylint: disable=protected-access
        )
