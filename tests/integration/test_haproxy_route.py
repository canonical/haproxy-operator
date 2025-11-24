# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ingress per unit relation."""

import json
import time

import httpx
import jubilant
import pytest
import requests

from .conftest import TEST_EXTERNAL_HOSTNAME_CONFIG
from .helper import get_http_version_from_apache2_logs, get_unit_ip_address


@pytest.mark.abort_on_fail
def test_haproxy_route_any_charm_requirer(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
):
    """Deploy the charm with anycharm ingress per unit requirer that installs apache2.

    Assert that the requirer endpoints are available.
    """
    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )
    # We set the removed retry-interval config option here as
    # ingress-configurator is not yet synced with the updated lib. This will be removed.
    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [80],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": True,
                    }
                ]
            ),
        },
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )
    haproxy_config = juju.ssh(
        f"{configured_application_with_tls}/0", "cat /etc/haproxy/haproxy.cfg"
    )
    assert all(
        entry in haproxy_config
        for entry in [
            "retries 3",
            "option redispatch",
            "option http-server-close",
            "balance source",
            "hash-type consistent",
        ]
    )
    juju.remove_relation(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )


@pytest.mark.abort_on_fail
def test_haproxy_route_protocol_https(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm haproxy route requirer that installs apache2 with ssl.
    Integrate haproxy with certificates and ca transfer.

    Assert that the requirer endpoints can be accessed using https.
    """
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )

    juju.integrate(
        f"{any_charm_haproxy_route_requirer}:require-tls-certificates",
        f"{certificate_provider_application}:certificates",
    )

    for _ in range(5):
        try:
            juju.run(
                f"{any_charm_haproxy_route_requirer}/0", "rpc", {"method": "start_ssl_server"}
            )
        except jubilant.TaskError:
            time.sleep(5)
            continue
        break
    else:
        raise AssertionError("Could not start anycharm ssl server")

    juju.integrate(
        f"{configured_application_with_tls}:receive-ca-certs",
        f"{certificate_provider_application}:send-ca-cert",
    )

    juju.integrate(
        f"{configured_application_with_tls}:haproxy-route", any_charm_haproxy_route_requirer
    )

    juju.run(
        f"{any_charm_haproxy_route_requirer}/0",
        "rpc",
        {
            "method": "update_relation",
            "args": json.dumps(
                [
                    {
                        "service": "any_charm_with_retry",
                        "ports": [443],
                        "retry_count": 3,
                        "retry_redispatch": True,
                        "load_balancing_algorithm": "source",
                        "load_balancing_consistent_hashing": True,
                        "http_server_close": True,
                        "protocol": "https",
                        "allow_http": True,
                    }
                ]
            ),
        },
    )

    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        ),
        delay=5,
    )

    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)
    response = requests.get(
        f"https://{haproxy_ip_address}",
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        timeout=5,
        verify=False,  # nosec: B501
    )
    assert response.text == "ok!"

    # Make HTTP request to verify allow_http works
    response = requests.get(
        f"http://{haproxy_ip_address}",
        headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
        timeout=5,
    )
    assert response.text == "ok!"


@pytest.mark.abort_on_fail
def test_haproxy_route_https_with_different_transport_protocols(
    configured_application_with_tls: str,
    any_charm_haproxy_route_requirer: str,
    juju: jubilant.Juju,
    certificate_provider_application: str,
):
    """Deploy the charm with anycharm haproxy route requirer that installs apache2 with ssl.
    Integrate haproxy with certificates and ca transfer.

    Assert that the communication between frontend<->haproxy and haproxy<->backend
        supports both http/2 and http/1.1 transport protocols.
    """
    juju.wait(
        lambda status: jubilant.all_active(
            status, configured_application_with_tls, any_charm_haproxy_route_requirer
        )
    )

    haproxy_ip_address = get_unit_ip_address(juju, configured_application_with_tls)

    # Test HTTP/1.1
    with httpx.Client(http2=False, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert response.http_version == "HTTP/1.1", (
            f"[frontend <-> haproxy] Expected HTTP/1.1, got {response.http_version} "
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer
    )
    assert http_transport_version == "HTTP/1.1", (
        f"[haproxy <-> backend] Expected HTTP/1.1, got {http_transport_version}"
    )

    # Test HTTP/2 without http/2 support on backend
    with httpx.Client(http2=True, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert response.http_version == "HTTP/2", (
            f"[frontend <-> haproxy] Expected HTTP/2, got {response.http_version}"
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer
    )
    assert http_transport_version == "HTTP/1.1", (
        f"[haproxy <-> backend] Expected HTTP/1.1, got {http_transport_version}"
    )

    # Test HTTP/2 with http/2 support on backend
    juju.ssh(
        f"{any_charm_haproxy_route_requirer}/0",
        "sudo a2enmod http2 && sudo systemctl restart apache2",
    )

    with httpx.Client(http2=True, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={
                "Host": TEST_EXTERNAL_HOSTNAME_CONFIG,
            },
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK
        assert response.http_version == "HTTP/2", (
            f"[frontend <-> haproxy] Expected HTTP/2, got {response.http_version}"
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer
    )
    assert http_transport_version == "HTTP/2.0", (
        f"[haproxy <-> backend] Expected HTTP/2, got {http_transport_version}"
    )

    # Test HTTP/1.1 without http/1.1 support on backend
    apache2_any_charm_conf = "/etc/apache2/sites-available/anycharm-ssl.conf"
    juju.ssh(
        f"{any_charm_haproxy_route_requirer}/0",
        rf"sudo sed -i '/<VirtualHost \*:443>/a\                Protocols h2' {apache2_any_charm_conf} &&"
        "sudo systemctl restart apache2",
    )

    with httpx.Client(http2=False, verify=False) as client:  # nosec: B501
        response = client.get(
            f"https://{haproxy_ip_address}",
            headers={"Host": TEST_EXTERNAL_HOSTNAME_CONFIG},
            timeout=5.0,
        )
        assert response.status_code == httpx.codes.OK, "HTTP/1.1 request failed"
        assert response.http_version == "HTTP/1.1", (
            f"[frontend <-> haproxy] Expected HTTP/1.1, got {response.http_version}"
        )

    http_transport_version = get_http_version_from_apache2_logs(
        juju, any_charm_haproxy_route_requirer
    )
    assert http_transport_version == "HTTP/2.0", (
        f"[haproxy <-> backend] Expected HTTP/2, got {http_transport_version}"
    )
