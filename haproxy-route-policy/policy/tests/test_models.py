# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for policy models."""

from django.test import TestCase

import policy.models as models


class RequestModelTestCase(TestCase):
    """Tests for the Request model."""

    def test_request_create(self):
        """Test creating a Request model instance."""
        request = models.Request.objects.create(
            requirer="00000000-0000-4000-8000-000000000000",
            domains=["example.com:80", "example.com:443"],
            auth=[models.AUTH_METHOD_NONE],
            src_ips=["10.0.0.1"],
            implicit_src_ips=False,
            status=models.PROXY_STATUS_PENDING,
            accepted_auth=None,
        )
        retrieved = models.Request.objects.get(pk=request.pk)
        self.assertEqual(str(retrieved.requirer), "00000000-0000-4000-8000-000000000000")
        self.assertEqual(retrieved.domains, ["example.com:80", "example.com:443"])
        self.assertEqual(retrieved.status, models.PROXY_STATUS_PENDING)

    def test_request_to_jsonable(self):
        """Test the to_jsonable method of Request."""
        request = models.Request.objects.create(
            requirer="00000000-0000-4000-8000-000000000000",
            domains=["example.com:80", "example.com:443"],
            auth=[models.AUTH_METHOD_NONE],
            src_ips=["10.0.0.1"],
            implicit_src_ips=False,
            status=models.PROXY_STATUS_PENDING,
            accepted_auth=None,
        )
        result = request.to_jsonable()
        self.assertEqual(result["requirer"], "00000000-0000-4000-8000-000000000000")
        self.assertEqual(result["domains"], ["example.com:80", "example.com:443"])
        self.assertEqual(result["auth"], [models.AUTH_METHOD_NONE])
        self.assertEqual(result["src_ips"], ["10.0.0.1"])
        self.assertFalse(result["implicit_src_ips"])
        self.assertEqual(result["status"], models.PROXY_STATUS_PENDING)
        self.assertIsNone(result["accepted_auth"])


class RequestInputValidationTestCase(TestCase):
    """Tests for RequestInput pydantic validation."""

    def test_valid_request_input(self):
        """Test valid request input passes validation."""
        validated = models.RequestInput(
            requirer="00000000-0000-4000-8000-000000000000",
            domains=["example.com"],
            auth=["none"],
            src_ips=["10.0.0.1"],
            implicit_src_ips=False,
        )
        self.assertEqual(
            str(validated.requirer), "00000000-0000-4000-8000-000000000000"
        )
        self.assertEqual(
            validated.domains, ("example.com:80", "example.com:443")
        )

    def test_invalid_domain_rejected(self):
        """Test that invalid domains are rejected."""
        with self.assertRaises(ValueError):
            models.RequestInput(
                requirer="00000000-0000-4000-8000-000000000000",
                domains=["not a valid domain!!!"],
                auth=["none"],
                src_ips=[],
                implicit_src_ips=False,
            )

    def test_invalid_auth_rejected(self):
        """Test that invalid auth methods are rejected."""
        with self.assertRaises(ValueError):
            models.RequestInput(
                requirer="00000000-0000-4000-8000-000000000000",
                domains=["example.com"],
                auth=["invalid_auth"],
                src_ips=[],
                implicit_src_ips=False,
            )

    def test_srcip_auth_requires_src_ips(self):
        """Test that srcip auth requires src_ips to be specified."""
        with self.assertRaises(ValueError):
            models.RequestInput(
                requirer="00000000-0000-4000-8000-000000000000",
                domains=["example.com"],
                auth=["srcip"],
                src_ips=[],
                implicit_src_ips=False,
            )

    def test_domain_canonicalization(self):
        """Test that domains are canonicalized with ports."""
        validated = models.RequestInput(
            requirer="00000000-0000-4000-8000-000000000000",
            domains=["example.com:8080"],
            auth=["none"],
            src_ips=[],
            implicit_src_ips=False,
        )
        self.assertEqual(validated.domains, ("example.com:8080",))

    def test_auth_ordering(self):
        """Test that auth methods are ordered correctly."""
        validated = models.RequestInput(
            requirer="00000000-0000-4000-8000-000000000000",
            domains=["example.com"],
            auth=["none", "srcip+userpass", "userpass"],
            src_ips=["10.0.0.1"],
            implicit_src_ips=False,
        )
        self.assertEqual(
            validated.auth,
            (
                models.AUTH_METHOD_SRCIP_USERPASS,
                models.AUTH_METHOD_USERPASS,
                models.AUTH_METHOD_NONE,
            ),
        )


class DomainParsingTestCase(TestCase):
    """Tests for domain parsing functions."""

    def test_parse_dns_domain(self):
        """Test parsing a standard DNS domain."""
        host, port = models.parse_domain("example.com")
        self.assertEqual(host, "example.com")
        self.assertEqual(port, 0)

    def test_parse_dns_domain_with_port(self):
        """Test parsing a DNS domain with port."""
        host, port = models.parse_domain("example.com:8080")
        self.assertEqual(host, "example.com")
        self.assertEqual(port, 8080)

    def test_parse_ipv4(self):
        """Test parsing an IPv4 address."""
        host, port = models.parse_domain("10.0.0.1")
        self.assertEqual(host, "10.0.0.1")
        self.assertEqual(port, 0)

    def test_parse_ipv4_with_port(self):
        """Test parsing an IPv4 address with port."""
        host, port = models.parse_domain("10.0.0.1:443")
        self.assertEqual(host, "10.0.0.1")
        self.assertEqual(port, 443)

    def test_parse_invalid_domain(self):
        """Test that invalid domains raise ValueError."""
        with self.assertRaises(ValueError):
            models.parse_domain("not valid!!!")
