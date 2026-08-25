# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration test for the log-hash-client-ip config option."""

import hashlib
import json
import socket
import ssl
import uuid
from urllib.parse import urlparse

import jubilant
import requests

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG, all_active_and_idle
from .helper import get_unit_address, get_unit_ip_address

LOG_HASH_SALT = "demo-salt-value"


def _last_client_field(juju: jubilant.Juju, unit: str, marker: str) -> str:
    """Return the client address field (IP:port) of the most recent haproxy access log.

    Logs are read from the journal rather than /var/log/haproxy.log because
    rsyslog file routing does not work in all environments (e.g. nested
    containers), while journald always captures haproxy's syslog output.
    """
    logs = juju.ssh(unit, "journalctl -u haproxy --no-pager -n 50")
    lines = [line for line in logs.splitlines() if " haproxy" in line and marker in line]
    assert lines, "no haproxy access log lines found"

    message = lines[-1].split("haproxy", 1)[1].split(None, 1)[1]
    return message.split()[0]


def _assert_hashed_http_request(
    juju: jubilant.Juju,
    unit: str,
    url: str,
    marker: str,
    expected_hash: str,
    client_ip: str,
    *,
    headers: dict[str, str] | None = None,
) -> None:
    """Send an HTTP request and assert that its client IP is hashed."""
    response = requests.get(
        url,
        headers=headers,
        verify=False,  # nosec
        timeout=30,
    )
    assert response.status_code == 200
    client_field = _last_client_field(juju, unit, marker)
    assert client_field.startswith(f"{expected_hash}:")
    assert not client_field.startswith(f"{client_ip}:")


def _remove_relation(
    juju: jubilant.Juju,
    relation: tuple[str, str],
    *applications: str,
) -> None:
    """Remove a relation and wait for its applications to settle."""
    juju.remove_relation(*relation)
    juju.wait(lambda status: all_active_and_idle(status, *applications))


def test_log_hash_client_ip(
    configured_application_with_tls: str,
    any_charm_ingress_requirer: str,
    any_charm_ingress_per_unit_requirer: str,
    any_charm_haproxy_route_requirer: str,
    any_charm_haproxy_route_tcp_requirer: str,
    juju: jubilant.Juju,
):
    """
    arrange: Deploy the charm.
    act: Toggle client IP hashing and send requests in default, ingress,
    ingress-per-unit, HAProxy-route HTTP, and mixed HTTP/TCP modes.
    assert: With the option disabled, the access log shows the client IP in
    plaintext. With it enabled, every mode logs the same salted SHA-256 hash.
    """
    application = configured_application_with_tls
    unit = f"{application}/0"
    juju.wait(lambda status: all_active_and_idle(status, application))
    address = get_unit_address(juju, application)

    juju.config(application, {"log-hash-client-ip": "false"})
    juju.wait(lambda status: all_active_and_idle(status, application))
    config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
    assert "log-format" not in config
    assert "error-log-format" not in config

    requests.get(f"{address}/", timeout=10)
    client_ip = _last_client_field(juju, unit, "GET").rsplit(":", 1)[0]
    assert client_ip, "expected a plaintext client IP in the access log"

    secret_uri = juju.add_secret(
        f"haproxy-log-hash-{uuid.uuid4().hex}",
        {"salt": LOG_HASH_SALT},
    )
    juju.grant_secret(secret_uri, application)
    created_relations: list[tuple[str, str]] = []
    try:
        juju.config(
            application,
            {
                "log-hash-client-ip": "true",
                "log-hash-salt": str(secret_uri),
            },
        )
        juju.wait(lambda status: all_active_and_idle(status, application))
        config = juju.ssh(unit, "cat /etc/haproxy/haproxy.cfg")
        assert "log-format" in config
        assert "error-log-format" in config
        assert "regsub(^::ffff:,)" in config
        assert "sha2(256)" in config

        # HAProxy's hex converter outputs uppercase.
        expected_hash = (
            hashlib.sha256(client_ip.encode() + LOG_HASH_SALT.encode()).hexdigest().upper()
        )
        _assert_hashed_http_request(
            juju,
            unit,
            f"{address}/?default-hash",
            "default-hash",
            expected_hash,
            client_ip,
        )

        ingress_relation = (
            f"{application}:ingress",
            f"{any_charm_ingress_requirer}:ingress",
        )
        juju.integrate(*ingress_relation)
        created_relations.append(ingress_relation)
        juju.wait(
            lambda status: all_active_and_idle(status, application, any_charm_ingress_requirer)
        )
        task = juju.run(
            f"{any_charm_ingress_requirer}/0",
            "rpc",
            {"method": "get_ingress_url"},
        )
        ingress_url_value = task.results.get("return") or task.results.get("result")
        assert isinstance(ingress_url_value, str)
        try:
            decoded_url = json.loads(ingress_url_value)
            if isinstance(decoded_url, str):
                ingress_url_value = decoded_url
        except json.JSONDecodeError:
            pass
        ingress_url = urlparse(ingress_url_value)
        ingress_marker = "ingress-hash"
        _assert_hashed_http_request(
            juju,
            unit,
            (f"{address.replace('http://', 'https://', 1)}{ingress_url.path}ok?{ingress_marker}"),
            ingress_marker,
            expected_hash,
            client_ip,
            headers={"Host": ingress_url.netloc},
        )
        _remove_relation(
            juju,
            ingress_relation,
            application,
            any_charm_ingress_requirer,
        )
        created_relations.remove(ingress_relation)

        ingress_per_unit_relation = (
            f"{application}:ingress-per-unit",
            f"{any_charm_ingress_per_unit_requirer}:require-ingress-per-unit",
        )
        juju.integrate(*ingress_per_unit_relation)
        created_relations.append(ingress_per_unit_relation)
        juju.wait(
            lambda status: all_active_and_idle(
                status, application, any_charm_ingress_per_unit_requirer
            )
        )
        ingress_per_unit_marker = "ingress-per-unit-hash"
        ingress_per_unit_path = (
            f"/{juju.model}-{any_charm_ingress_per_unit_requirer}/0/ok?{ingress_per_unit_marker}"
        )
        _assert_hashed_http_request(
            juju,
            unit,
            f"{address.replace('http://', 'https://', 1)}{ingress_per_unit_path}",
            ingress_per_unit_marker,
            expected_hash,
            client_ip,
            headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        )
        _remove_relation(
            juju,
            ingress_per_unit_relation,
            application,
            any_charm_ingress_per_unit_requirer,
        )
        created_relations.remove(ingress_per_unit_relation)

        juju.run(f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "start_server"})
        http_relation = (
            f"{application}:haproxy-route",
            any_charm_haproxy_route_requirer,
        )
        juju.integrate(*http_relation)
        created_relations.append(http_relation)
        juju.run(
            f"{any_charm_haproxy_route_requirer}/0",
            "rpc",
            {
                "method": "update_relation",
                "args": json.dumps(
                    [
                        {
                            "service": "hash-test-http",
                            "ports": [80],
                        }
                    ]
                ),
            },
        )
        juju.wait(
            lambda status: all_active_and_idle(
                status, application, any_charm_haproxy_route_requirer
            )
        )
        haproxy_route_marker = "haproxy-route-hash"
        _assert_hashed_http_request(
            juju,
            unit,
            (f"{address.replace('http://', 'https://', 1)}/?{haproxy_route_marker}"),
            haproxy_route_marker,
            expected_hash,
            client_ip,
            headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        )

        tcp_relation = (
            f"{application}:haproxy-route-tcp",
            any_charm_haproxy_route_tcp_requirer,
        )
        juju.integrate(*tcp_relation)
        created_relations.append(tcp_relation)
        juju.run(
            f"{any_charm_haproxy_route_tcp_requirer}/0",
            "rpc",
            {"method": "update_relation"},
        )
        juju.wait(
            lambda status: all_active_and_idle(
                status,
                application,
                any_charm_haproxy_route_requirer,
                any_charm_haproxy_route_tcp_requirer,
            )
        )

        haproxy_ip_address = get_unit_ip_address(juju, application)
        mixed_mode_marker = "mixed-mode-hash"
        _assert_hashed_http_request(
            juju,
            unit,
            f"{address.replace('http://', 'https://', 1)}/?{mixed_mode_marker}",
            mixed_mode_marker,
            expected_hash,
            client_ip,
            headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        )

        context = ssl._create_unverified_context()  # pylint: disable=protected-access  # nosec
        with (
            socket.create_connection((str(haproxy_ip_address), 4444), timeout=30) as sock,
            context.wrap_socket(sock, server_hostname="example.com") as secure_socket,
        ):
            secure_socket.sendall(b"ping")
            assert b"pong" in secure_socket.read()

        hashed_tcp_client = _last_client_field(juju, unit, "haproxy_route_tcp_4444")
        assert hashed_tcp_client.startswith(f"{expected_hash}:")
        assert not hashed_tcp_client.startswith(f"{client_ip}:")
    finally:
        for relation in reversed(created_relations):
            juju.remove_relation(*relation)
        juju.config(application, {"log-hash-client-ip": "false"})
        juju.cli("config", application, "--reset", "log-hash-salt")
        juju.wait(lambda status: all_active_and_idle(status, application))
        juju.remove_secret(secret_uri)
