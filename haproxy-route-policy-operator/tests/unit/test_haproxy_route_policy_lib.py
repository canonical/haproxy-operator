# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for haproxy-route-policy interface library models."""

import pytest
from charms.haproxy_route_policy.v0.haproxy_route_policy import (
    HaproxyRoutePolicyBackendRequest,
    HaproxyRoutePolicyProviderAppData,
    HaproxyRoutePolicyRequirerAppData,
    valid_domain_with_wildcard,
)
from pydantic import ValidationError

VALID_BACKEND_REQUEST = {
    "relation_id": 10,
    "backend_name": "backend-a",
    "hostname_acls": ["example.com"],
    "paths": ["/"],
    "port": 8080,
}


@pytest.mark.parametrize(
    "domain",
    [
        pytest.param("example.com", id="fqdn"),
        pytest.param("api.example.com", id="subdomain"),
        pytest.param("*.example.com", id="wildcard"),
    ],
)
def test_valid_domain_with_wildcard_accepts_valid_domain(domain: str):
    """
    arrange: provide a valid domain.
    act: call valid_domain_with_wildcard.
    assert: returns the same domain.
    """
    assert valid_domain_with_wildcard(domain) == domain


@pytest.mark.parametrize(
    "domain",
    [
        pytest.param("", id="empty"),
        pytest.param("example", id="missing-tld"),
        pytest.param("*.com", id="wildcard-tld"),
        pytest.param("invalid host", id="space-in-host"),
    ],
)
def test_valid_domain_with_wildcard_rejects_invalid_domain(domain: str):
    """
    arrange: provide an invalid domain.
    act: call valid_domain_with_wildcard.
    assert: raises ValueError.
    """
    with pytest.raises(ValueError):
        valid_domain_with_wildcard(domain)


def test_backend_request_model_validation_accepts_valid_payload():
    """
    arrange: build a valid backend request payload.
    act: initialize HaproxyRoutePolicyBackendRequest.
    assert: fields are parsed correctly.
    """
    request = HaproxyRoutePolicyBackendRequest(**VALID_BACKEND_REQUEST)

    assert request.relation_id == 10
    assert request.backend_name == "backend-a"
    assert request.hostname_acls == ["example.com"]
    assert request.paths == ["/"]
    assert request.port == 8080


@pytest.mark.parametrize(
    "field,value",
    [
        pytest.param("port", 0, id="port-too-low"),
        pytest.param("port", 65536, id="port-too-high"),
        pytest.param("hostname_acls", ["invalid host"], id="invalid-hostname"),
    ],
)
def test_backend_request_model_validation_rejects_invalid_payload(field: str, value):
    """
    arrange: build an invalid backend request payload.
    act: initialize HaproxyRoutePolicyBackendRequest.
    assert: raises ValidationError.
    """
    payload = VALID_BACKEND_REQUEST.copy()
    payload[field] = value

    with pytest.raises(ValidationError):
        HaproxyRoutePolicyBackendRequest(**payload)


def test_requirer_app_data_model_accepts_valid_payload():
    """
    arrange: build valid requirer app data.
    act: initialize HaproxyRoutePolicyRequirerAppData.
    assert: payload is validated and fields are preserved.
    """
    request = HaproxyRoutePolicyBackendRequest(**VALID_BACKEND_REQUEST)
    app_data = HaproxyRoutePolicyRequirerAppData(backend_requests=[request])

    assert len(app_data.backend_requests) == 1
    assert app_data.backend_requests[0].backend_name == "backend-a"
    assert app_data.backend_requests[0].port == 8080


def test_provider_app_data_model_accepts_valid_payload():
    """
    arrange: build valid provider app data.
    act: initialize HaproxyRoutePolicyProviderAppData.
    assert: payload is validated and fields are preserved.
    """
    request = HaproxyRoutePolicyBackendRequest(**VALID_BACKEND_REQUEST)
    app_data = HaproxyRoutePolicyProviderAppData(
        approved_requests=[request], policy_backend_port=8080, model="test-model"
    )

    assert len(app_data.approved_requests) == 1
    assert app_data.approved_requests[0].backend_name == "backend-a"
    assert app_data.approved_requests[0].relation_id == 10


def test_requirer_app_data_rejects_duplicate_backend_names():
    """
    arrange: build app data payload with duplicate backend names.
    act: initialize HaproxyRoutePolicyRequirerAppData.
    assert: raises ValidationError.
    """
    duplicated_requests = [
        HaproxyRoutePolicyBackendRequest(**VALID_BACKEND_REQUEST),
        HaproxyRoutePolicyBackendRequest(
            **{
                **VALID_BACKEND_REQUEST,
                "relation_id": 11,
                "port": 9090,
                "hostname_acls": ["api.example.com"],
            }
        ),
    ]

    with pytest.raises(ValidationError):
        HaproxyRoutePolicyRequirerAppData(backend_requests=duplicated_requests)
