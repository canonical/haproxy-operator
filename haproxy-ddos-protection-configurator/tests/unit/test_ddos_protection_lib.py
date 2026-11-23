# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for DDoS protection interface library."""

from charms.haproxy.v0.ddos_protection import DDoSProtectionProviderAppData


def test_ddos_protection_provider_app_data_ip_allow_list():
    """
    arrange: Create DDoS protection data with IPv4 and IPv6 addresses and CIDR blocks.
    act: Validate the model.
    assert: All entries are correctly converted.
    """
    data = DDoSProtectionProviderAppData(
        rate_limit_requests_per_minute=100,
        ip_allow_list=["192.168.0.0/16", "10.0.0.1", "2001:db8::1", "2001:db8:abcd::/48"],
    )

    assert [str(ip) for ip in data.ip_allow_list] == [
        "192.168.0.0/16",
        "10.0.0.1",
        "2001:db8::1",
        "2001:db8:abcd::/48",
    ]
