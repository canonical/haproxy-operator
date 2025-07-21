# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper methods for integration tests."""

import json
from urllib.parse import ParseResult, urlparse

import yaml
from juju.application import Application
from pytest_operator.plugin import OpsTest
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES, HTTPAdapter


class DNSResolverHTTPSAdapter(HTTPAdapter):
    """A simple mounted DNS resolver for HTTP requests."""

    def __init__(
        self,
        hostname,
        ip,
    ):
        """Initialize the dns resolver.

        Args:
            hostname: DNS entry to resolve.
            ip: Target IP address.
        """
        self.hostname = hostname
        self.ip = ip
        super().__init__(
            pool_connections=DEFAULT_POOLSIZE,
            pool_maxsize=DEFAULT_POOLSIZE,
            max_retries=DEFAULT_RETRIES,
            pool_block=DEFAULT_POOLBLOCK,
        )

    # Ignore pylint rule as this is the parent method signature
    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):  # pylint: disable=too-many-arguments, too-many-positional-arguments
        """Wrap HTTPAdapter send to modify the outbound request.

        Args:
            request: Outbound HTTP request.
            stream: argument used by parent method.
            timeout: argument used by parent method.
            verify: argument used by parent method.
            cert: argument used by parent method.
            proxies: argument used by parent method.

        Returns:
            Response: HTTP response after modification.
        """
        connection_pool_kwargs = self.poolmanager.connection_pool_kw

        result = urlparse(request.url)
        if result.hostname == self.hostname:
            ip = self.ip
            if result.scheme == "https" and ip:
                request.url = request.url.replace(
                    "https://" + result.hostname,
                    "https://" + ip,
                )
                connection_pool_kwargs["server_hostname"] = result.hostname
                connection_pool_kwargs["assert_hostname"] = result.hostname
                request.headers["Host"] = result.hostname
            else:
                connection_pool_kwargs.pop("server_hostname", None)
                connection_pool_kwargs.pop("assert_hostname", None)

        return super().send(request, stream, timeout, verify, cert, proxies)


async def get_ingress_url_for_application(
    ingress_requirer_application: Application, ops_test: OpsTest
) -> ParseResult:
    """Get the ingress url from the requirer's unit data.

    Args:
        ingress_requirer_application: Requirer application.
        ops_test: OpsTest framework to run juju show-unit.

    Returns:
        ParseResult: The parsed ingress url.
    """
    unit_name = ingress_requirer_application.units[0].name
    _, stdout, _ = await ops_test.juju("show-unit", unit_name, "--format", "json")
    unit_information = json.loads(stdout)[unit_name]
    ingress_integration_data = json.loads(
        unit_information["relation-info"][0]["application-data"]["ingress"]
    )
    return urlparse(ingress_integration_data["url"])


async def get_ingress_per_unit_urls_for_application(
    ingress_per_unit_requirer_application: Application, ops_test: OpsTest
) -> list[ParseResult]:
    """Get the list of ingress urls per unit from the requirer's unit data.

    Args:
        ingress_per_unit_requirer_application: Requirer application.
        ops_test: OpsTest framework to run juju show-unit.

    Returns:
        list: The parsed ingress urls per unit.
    """
    unit_name = ingress_per_unit_requirer_application.units[0].name
    _, stdout, _ = await ops_test.juju("show-unit", unit_name, "--format", "json")
    unit_information = json.loads(stdout)[unit_name]
    for rel in unit_information["relation-info"]:
        if rel["related-endpoint"] == "ingress-per-unit":
            ingress_per_unit_data = rel["application-data"].get("ingress")
            break
    parsed_yaml = yaml.safe_load(ingress_per_unit_data)
    return [urlparse(data["url"]) for _, data in parsed_yaml.items()]
