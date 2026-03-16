# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for policy API views."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

import policy.models as models


class RequestsAPITestCase(APITestCase):
    """Tests for the requests API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user("admin", "admin@example.com", "admin")
        self.client = APIClient()

    def login(self):
        self.client.login(username="admin", password="admin")

    def generate_example_proxy_requests(self):
        return [
            {
                "requirer": "00000000-0000-4000-8000-000000000000",
                "domains": ["example.com"],
                "auth": ["none"],
                "src_ips": ["10.0.0.1"],
                "implicit_src_ips": False,
            },
            {
                "requirer": "00000000-0000-4000-9000-000000000000",
                "domains": ["ubuntu.com"],
                "auth": ["srcip+userpass", "srcip", "userpass", "none"],
                "src_ips": ["192.168.0.1", "192.168.0.2"],
                "implicit_src_ips": True,
            },
            {
                "requirer": "00000000-0000-4000-a000-000000000000",
                "domains": ["github.com"],
                "auth": ["userpass", "none"],
                "src_ips": ["172.16.0.1", "172.16.0.2"],
                "implicit_src_ips": True,
            },
        ]

    def bulk_create_requests(self, requests):
        response = self.client.post(
            reverse("api-list-create-requests"),
            data=requests,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_list_requests_empty(self):
        """Test listing requests when none exist returns empty list."""
        self.login()
        response = self.client.get(reverse("api-list-create-requests"))
        self.assertEqual(response.status_code, 200)
        self.assertSequenceEqual(response.json(), [])

    def test_bulk_create_requests_empty(self):
        """Test bulk creating with an empty list returns empty list."""
        self.login()
        response = self.client.post(
            reverse("api-list-create-requests"), data=[], format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertSequenceEqual(response.json(), [])

    def test_bulk_create_requests(self):
        """Test bulk creating proxy requests sets them to pending."""
        self.login()
        result = self.bulk_create_requests(
            self.generate_example_proxy_requests()
        )
        self.assertSequenceEqual(
            result,
            [
                {
                    "requirer": "00000000-0000-4000-8000-000000000000",
                    "domains": ["example.com:80", "example.com:443"],
                    "auth": [models.AUTH_METHOD_NONE],
                    "src_ips": ["10.0.0.1"],
                    "implicit_src_ips": False,
                    "status": "pending",
                    "accepted_auth": None,
                },
                {
                    "requirer": "00000000-0000-4000-9000-000000000000",
                    "domains": ["ubuntu.com:80", "ubuntu.com:443"],
                    "auth": [
                        models.AUTH_METHOD_SRCIP_USERPASS,
                        models.AUTH_METHOD_USERPASS,
                        models.AUTH_METHOD_SRCIP,
                        models.AUTH_METHOD_NONE,
                    ],
                    "src_ips": ["192.168.0.1", "192.168.0.2"],
                    "implicit_src_ips": True,
                    "status": "pending",
                    "accepted_auth": None,
                },
                {
                    "requirer": "00000000-0000-4000-a000-000000000000",
                    "domains": ["github.com:80", "github.com:443"],
                    "auth": [
                        models.AUTH_METHOD_USERPASS,
                        models.AUTH_METHOD_NONE,
                    ],
                    "src_ips": ["172.16.0.1", "172.16.0.2"],
                    "implicit_src_ips": True,
                    "status": "pending",
                    "accepted_auth": None,
                },
            ],
        )

    def test_bulk_create_replaces_existing(self):
        """Test that bulk create replaces all existing requests."""
        self.login()
        self.bulk_create_requests(self.generate_example_proxy_requests())

        new_requests = [
            {
                "requirer": "00000000-0000-4000-b000-000000000000",
                "domains": ["new-domain.com"],
                "auth": ["none"],
                "src_ips": [],
                "implicit_src_ips": False,
            },
        ]
        result = self.bulk_create_requests(new_requests)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["requirer"], "00000000-0000-4000-b000-000000000000")

        response = self.client.get(reverse("api-list-create-requests"))
        self.assertEqual(len(response.json()), 1)

    def test_bulk_create_invalid_json(self):
        """Test that invalid JSON returns 400."""
        self.login()
        response = self.client.post(
            reverse("api-list-create-requests"),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_bulk_create_not_list(self):
        """Test that non-list JSON returns 400."""
        self.login()
        response = self.client.post(
            reverse("api-list-create-requests"),
            data={"not": "a list"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_bulk_create_duplicate_requirer(self):
        """Test that duplicate requirer in the same request returns 400."""
        self.login()
        requests = [
            {
                "requirer": "00000000-0000-4000-8000-000000000000",
                "domains": ["example.com"],
                "auth": ["none"],
                "src_ips": [],
                "implicit_src_ips": False,
            },
            {
                "requirer": "00000000-0000-4000-8000-000000000000",
                "domains": ["example.com"],
                "auth": ["none"],
                "src_ips": [],
                "implicit_src_ips": False,
            },
        ]
        response = self.client.post(
            reverse("api-list-create-requests"),
            data=requests,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_bulk_create_missing_requirer(self):
        """Test that missing requirer field returns 400."""
        self.login()
        requests = [
            {
                "domains": ["example.com"],
                "auth": ["none"],
                "src_ips": [],
                "implicit_src_ips": False,
            },
        ]
        response = self.client.post(
            reverse("api-list-create-requests"),
            data=requests,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_bulk_create_invalid_domain(self):
        """Test that invalid domain returns 400."""
        self.login()
        requests = [
            {
                "requirer": "00000000-0000-4000-8000-000000000000",
                "domains": ["not valid!!!"],
                "auth": ["none"],
                "src_ips": [],
                "implicit_src_ips": False,
            },
        ]
        response = self.client.post(
            reverse("api-list-create-requests"),
            data=requests,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_request_by_id(self):
        """Test getting a single request by its UUID."""
        self.login()
        self.bulk_create_requests(self.generate_example_proxy_requests())

        uuid = "00000000-0000-4000-8000-000000000000"
        response = self.client.get(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "requirer": "00000000-0000-4000-8000-000000000000",
                "domains": ["example.com:80", "example.com:443"],
                "auth": [models.AUTH_METHOD_NONE],
                "src_ips": ["10.0.0.1"],
                "implicit_src_ips": False,
                "status": "pending",
                "accepted_auth": None,
            },
        )

    def test_get_request_not_found(self):
        """Test getting a non-existent request returns 404."""
        self.login()
        uuid = "00000000-0000-4000-8000-000000000000"
        response = self.client.get(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_request(self):
        """Test deleting a request by ID."""
        self.login()
        self.bulk_create_requests(self.generate_example_proxy_requests())

        uuid = "00000000-0000-4000-8000-000000000000"
        response = self.client.delete(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_request_not_found(self):
        """Test deleting a non-existent request returns 404."""
        self.login()
        uuid = "00000000-0000-4000-8000-000000000000"
        response = self.client.delete(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertEqual(response.status_code, 404)

    def test_list_requests_filter_by_status(self):
        """Test listing requests filtered by status."""
        self.login()
        self.bulk_create_requests(self.generate_example_proxy_requests())

        response = self.client.get(
            reverse("api-list-create-requests"), {"status": "pending"}
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(len(result), 3)
        for r in result:
            self.assertEqual(r["status"], "pending")

        response = self.client.get(
            reverse("api-list-create-requests"), {"status": "accepted"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_list_requests_without_filter(self):
        """Test listing all requests without status filter."""
        self.login()
        self.bulk_create_requests(self.generate_example_proxy_requests())

        response = self.client.get(reverse("api-list-create-requests"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied."""
        response = self.client.get(reverse("api-list-create-requests"))
        self.assertIn(response.status_code, [401, 403])

        response = self.client.post(
            reverse("api-list-create-requests"), data=[], format="json"
        )
        self.assertIn(response.status_code, [401, 403])

        uuid = "00000000-0000-4000-8000-000000000000"
        response = self.client.get(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertIn(response.status_code, [401, 403])

        response = self.client.delete(
            reverse("api-get-delete-request", args=(uuid,))
        )
        self.assertIn(response.status_code, [401, 403])
