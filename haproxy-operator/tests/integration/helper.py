# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# pylint: disable=duplicate-code

"""Helper methods for integration tests."""

import ipaddress
import json
import re
import typing
from urllib.parse import ParseResult, urlparse

import jubilant
import pytest
import yaml
from requests.adapters import DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE, DEFAULT_RETRIES, HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_fixed

HTTP_TRANSPORT_VERSION_PATTERN = re.compile(r"HTTP/[\d\.]+")


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
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):  # pylint: disable=too-many-arguments, too-many-positional-arguments
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


def get_ingress_per_unit_urls_for_application(
    juju: jubilant.Juju, app_name: str
) -> list[ParseResult]:
    """Get the list of ingress URLs per unit from the requirer's unit data.

    Args:
        juju: Jubilant Juju client.
        app_name: Requirer application name.

    Returns:
        list: The parsed ingress URLs per unit.
    """
    unit_name = f"{app_name}/0"
    result = juju.cli("show-unit", unit_name, "--format", "json")
    unit_info = json.loads(result)[unit_name]

    for rel in unit_info["relation-info"]:
        if rel["related-endpoint"] == "ingress-per-unit":
            ingress_data = rel["application-data"].get("ingress")
            break

    parsed_yaml = yaml.safe_load(ingress_data)
    return [urlparse(data["url"]) for _, data in parsed_yaml.items()]


def get_unit_ip_address(
    juju: jubilant.Juju,
    application: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Get the unit IP address of a Juju application to make HTTP requests.

    Args:
        juju: Jubilant Juju instance.
        application: The name of the deployed application.

    Returns:
        The IP address of the first unit.
    """
    status = juju.status()
    app_status = status.apps.get(application)
    assert app_status, f"Application {application} not found in model status"
    unit_status = next(iter(app_status.units.values()))
    address = unit_status.public_address
    assert address, f"Unit of {application} has no public address"
    return ipaddress.ip_address(address)


def get_unit_address(juju: jubilant.Juju, application: str) -> str:
    """Get the HTTP address of the first unit of a Juju application.

    Args:
        juju: Jubilant Juju instance.
        application: The name of the deployed application.

    Returns:
        A string representing the base HTTP URL for the first unit.
    """
    unit_ip_address = get_unit_ip_address(juju, application)
    if isinstance(unit_ip_address, ipaddress.IPv6Address):
        return f"http://[{unit_ip_address}]"
    return f"http://{unit_ip_address}"


def pytestconfig_arg_no_deploy(application: str) -> typing.Callable:
    """Create a decorator that handles the --no-deploy config.

    Args:
        application: The application to deploy.

    Returns:
        the function decorator.
    """

    def decorator(
        method: typing.Callable,
    ) -> typing.Callable:
        """Create a decorator that handles the --no-deploy config.

        Args:
            method: observer method to wrap.

        Returns:
            the function wrapper.
        """

        def wrapper(pytestconfig: pytest.Config, juju: jubilant.Juju, *args: typing.Any) -> str:
            """Block the charm if the config is wrong.

            Args:
                pytestconfig: Contains parameters passed to the test.
                juju: jubilant fixture
                args: Additional arguments

            Returns:
                The value returned from the original function. That is, None.
            """
            if pytestconfig.getoption("--no-deploy") and application in juju.status().apps:
                return application
            return method(pytestconfig, juju, *args)

        return wrapper

    return decorator


def get_http_version_from_apache2_logs(
    juju: jubilant.Juju,
    app_name: str,
    request_id: str,
    pattern: re.Pattern = HTTP_TRANSPORT_VERSION_PATTERN,
) -> str:
    """
    Extract the HTTP transport version from the apache2 access logs of a given application unit.

    Args:
        juju: Jubilant Juju client.
        app_name: The name of the application whose logs to check.
        pattern: The regex pattern to extract the HTTP version.

    Returns:
        The extracted HTTP version string.
    """
    last_httpx_log_entry = juju.ssh(
        f"{app_name}/0",
        f"grep '{request_id}' /var/log/apache2/access.log | tail -n 1",
    )

    match = pattern.search(last_httpx_log_entry)
    if not match:
        raise RuntimeError("Unexpected Error: No HTTP version found in log entry")

    return match.group(0)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(30))
def verify_relations_removed(
    juju: jubilant.Juju,
    app_name: str,
    relations_to_remove: list[tuple[str, str]],
) -> None:
    """Verify that relations have been removed with retries.

    Args:
        juju: Jubilant Juju client.
        app_name: The application name to check.
        relations_to_remove: List of (endpoint, related_app) tuples to verify removal.

    Raises:
        AssertionError: If any relation still exists after retries.
    """
    for endpoint, related_app in relations_to_remove:
        rels = juju.status().apps[app_name].relations.get(endpoint, [])
        if any(relation.related_app == related_app for relation in rels):
            raise AssertionError(
                f"Relation {endpoint} with {related_app} still exists"
            )
