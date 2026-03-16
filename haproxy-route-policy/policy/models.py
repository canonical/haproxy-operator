# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Database models and validation schemas for the policy application."""

import collections
import ipaddress
import re
import uuid
from typing import Annotated, Sequence

from django.db import models
from pydantic import BaseModel, BeforeValidator, model_validator

AUTH_METHOD_SRCIP_USERPASS = "srcip+userpass"
AUTH_METHOD_USERPASS = "userpass"
AUTH_METHOD_SRCIP = "srcip"
AUTH_METHOD_NONE = "none"
AUTH_METHODS = [
    AUTH_METHOD_SRCIP_USERPASS,
    AUTH_METHOD_USERPASS,
    AUTH_METHOD_SRCIP,
    AUTH_METHOD_NONE,
]

PROXY_STATUS_PENDING = "pending"
PROXY_STATUS_ACCEPTED = "accepted"
PROXY_STATUS_REJECTED = "rejected"
PROXY_STATUSES = [
    PROXY_STATUS_PENDING,
    PROXY_STATUS_ACCEPTED,
    PROXY_STATUS_REJECTED,
]


def dedup(input_list: list[str]) -> list[str]:
    """Deduplicate a list without changing the order.

    Args:
        input_list: The input list.

    Returns:
        The deduplicated list.
    """
    seen = set()
    result = []
    for i in input_list:
        if i in seen:
            continue
        seen.add(i)
        result.append(i)
    return result


def parse_domain(domain: str) -> tuple[str, int]:
    """Parse a domain string in the form of host[:port].

    Args:
        domain: The domain string.

    Returns:
        A (host, port) tuple. Port is 0 if not specified.

    Raises:
        ValueError: If the domain string is invalid.
    """
    host: str
    port: int | str
    if domain.startswith("["):
        if "]:" in domain:
            host, port = domain.rsplit("]:", maxsplit=1)
            host = host.removeprefix("[")
        else:
            host = domain.removeprefix("[").removesuffix("]")
            port = 0
        ipaddress.ip_network(host, strict=False)
        host = f"[{host}]"
    elif domain.count(":") >= 2:
        ipaddress.ip_network(domain, strict=False)
        host, port = f"[{domain}]", 0
    elif re.match("^[0-9.:]+$", domain):
        if ":" in domain:
            host, port = domain.rsplit(":", 1)
        else:
            host, port = domain, 0
        ipaddress.ip_address(host)
    else:
        match = re.match(
            r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*"
            r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])"
            r"(:[0-9]+)?$",
            domain,
        )
        if not match:
            raise ValueError(f"invalid domain: {domain}")
        if ":" in domain:
            host, port = domain.rsplit(":", 1)
        else:
            host, port = domain, 0
    return host, int(port)


def _validate_and_transform_domains(domains: Sequence[str]) -> tuple[str, ...]:
    """Validate and transform the domains input.

    Args:
        domains: The input domains.

    Returns:
        The canonical representation of the domains.
    """
    if not domains:
        raise ValueError("no domains specified")
    valid_domains = []
    invalid_domains = []
    for domain in domains:
        try:
            host, port = parse_domain(domain)
            if not 0 <= port <= 65535:
                raise ValueError(f"invalid port: {port}")
            if port != 0:
                valid_domains.append(f"{host}:{port}")
            else:
                valid_domains.append(f"{host}:80")
                valid_domains.append(f"{host}:443")
        except ValueError:
            invalid_domains.append(domain)
    if invalid_domains:
        raise ValueError(f"invalid domains: {invalid_domains}")
    return tuple(dedup(sorted(valid_domains, key=parse_domain)))


def _validate_and_transform_auth(auth: Sequence[str]) -> tuple[str, ...]:
    """Validate and transform the auth input.

    Args:
        auth: The input auth.

    Returns:
        The canonical representation of the auth.
    """
    if not auth:
        raise ValueError("no auth method specified")
    invalid_auth = [a for a in auth if a not in AUTH_METHODS]
    if invalid_auth:
        raise ValueError(f"invalid auth type: {invalid_auth}")
    sorted_auth = dedup(sorted(auth, key=AUTH_METHODS.index))
    return tuple(sorted_auth)


def _validate_and_sort_src_ip(src_ips: Sequence[str]) -> tuple[str, ...]:
    """Validate and transform the src_ips input.

    Args:
        src_ips: The input src_ips.

    Returns:
        The canonical representation of the src_ips.
    """
    if src_ips is None:
        return tuple()
    validated_ips = []
    invalid_ips = []
    for ip in src_ips:
        try:
            ipaddress.ip_network(ip, strict=False)
            validated_ips.append(ip)
        except ValueError:
            invalid_ips.append(ip)
    if invalid_ips:
        raise ValueError(f"invalid src_ips: {invalid_ips}")
    return tuple(dedup(sorted(validated_ips)))


def compact_domains(domains: Sequence[str]) -> list[str]:
    """Convert domain list to compact format, merging :80/:443 pairs.

    Args:
        domains: The domain list.

    Returns:
        The compacted domain list.
    """
    host_port = collections.defaultdict(list)
    for domain in domains:
        host, port = parse_domain(domain)
        host_port[host].append(port)
    result = []
    for host, ports in host_port.items():
        if 80 in ports and 443 in ports:
            result.append(host)
            ports.remove(80)
            ports.remove(443)
        for port in ports:
            result.append(f"{host}:{port}")
    return result


class RequestInput(BaseModel):
    """Pydantic model for validating request input data."""

    requirer: uuid.UUID
    domains: Annotated[
        tuple[str, ...], BeforeValidator(_validate_and_transform_domains)
    ]
    auth: Annotated[tuple[str, ...], BeforeValidator(_validate_and_transform_auth)]
    src_ips: Annotated[tuple[str, ...], BeforeValidator(_validate_and_sort_src_ip)]
    implicit_src_ips: bool

    @model_validator(mode="after")
    def _validate(self) -> "RequestInput":
        """Validate the object as a whole.

        Returns:
            The validated object.
        """
        if (
            any(
                auth in (AUTH_METHOD_SRCIP, AUTH_METHOD_SRCIP_USERPASS)
                for auth in self.auth
            )
            and not self.src_ips
        ):
            raise ValueError("no src_ips specified for srcip authentication")
        return self


class Request(models.Model):
    """Database model for proxy requests."""

    requirer = models.UUIDField(primary_key=True)
    domains = models.JSONField()
    auth = models.JSONField()
    src_ips = models.JSONField()
    implicit_src_ips = models.BooleanField()
    status = models.TextField(
        choices={
            PROXY_STATUS_ACCEPTED: PROXY_STATUS_ACCEPTED,
            PROXY_STATUS_REJECTED: PROXY_STATUS_REJECTED,
            PROXY_STATUS_PENDING: PROXY_STATUS_PENDING,
        },
        db_index=True,
    )
    accepted_auth = models.TextField(null=True)

    def to_jsonable(self) -> dict:
        """Convert the model instance to a JSON-serializable dictionary.

        Returns:
            A dictionary representation of the request.
        """
        return {
            "requirer": str(self.requirer),
            "domains": self.domains,
            "auth": self.auth,
            "src_ips": self.src_ips,
            "implicit_src_ips": self.implicit_src_ips,
            "status": self.status,
            "accepted_auth": self.accepted_auth,
        }
