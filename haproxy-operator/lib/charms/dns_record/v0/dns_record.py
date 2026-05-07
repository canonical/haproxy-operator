# Copyright 2026 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.

r"""Library to manage the integration with a primary DNS charm.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.
It is completely backwards compatible with the legacy bind.v0.dns_record library.

### Requirer Charm

```python

from charms.dns_record.v0 import dns_record

class DNSRecordRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.framework.observe(self.dns_record.on.relation_joined, self._handler)
        ...

    def _handler(self, events: RelationJoinedEvent) -> None:
        self._update_relations()

    def _update_relations(self) -> None:
        if not self.model.unit.is_leader():
            return
        try:
            self.dns_record.update_relation_data(self._get_dns_record_data())
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)
            raise

    def _get_dns_record_data(self) -> list[dns_record.RecordRequest]:
        entries = []
        for request in str(self.config["requests"]).split("\n"):
            try:
                entries.append(self.dns_record.create_record_request(request))
            except dns_record.CreateRecordRequestError:
                logger.error("Invalid entry ignored: '%s'", request)
                continue
        return entries

```

As shown above, the library does not expose any custom event and the user has to rely
on the generic RelationJoined, RelationChanged events to check when DNS data has been changed.

The DNSRecordRequires provides an `update_relation_data` method to update the relation data by
passing a list of RecordRequest, requesting new DNS records.

### Provider Charm

Following the previous example, this is an example of the provider charm.

```python
from charms.bind.v0.dns_record import DNSRecordProvides

class DNSRecordProviderCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = DNSRecordProvides(self)
        ...

```
The DNSRecordProvides object wraps the list of relations into a `relations` property
and provides an `update_relation_data` method to update the relation data by passing
a list of RecordRequest. It is expected that the provider updates the status of
those requests before updating the relation data.

```python
class DNSRecordProviderCharm(ops.CharmBase):
    ...

    def _handler(self, _: RelationChangedEvent) -> None:

        for relation in self.model.relations[self.dns_record.relation_name]:
        requests = dns_record.get_relation_data()
        for request in requests:
            request.status = Status.APPROVED
        self.dns_record.update_relation_data(requests)

```
"""

# This is a rewrite of bind.v0.dns_record
# there will be duplicate code
# pylint: disable=duplicate-code

# The unique Charmhub library identifier, never change it
LIBID = "74dd8fda03d94f4c2a113da921cf099c"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import collections
import itertools
import json
import logging
import typing
import uuid as uuid_module
from enum import Enum

import ops
import pydantic

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns-record"
DEFAULT_SECRET_LABEL = "dns-record"  # nosec


class DnsRecordError(Exception):
    """Base exception for the lib."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class CreateRecordRequestError(DnsRecordError):
    """Exception raised creating the record request fails."""


class Status(str, Enum):
    """Represent the status values.

    Attributes:
        APPROVED: approved
        PERMISSION_DENIED: permission_denied
        CONFLICT: conflict
        INVALID_DATA: invalid_data
        FAILURE: failure
        UNKNOWN: unknown
        PENDING: pending
    """

    APPROVED = "approved"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    INVALID_DATA = "invalid_data"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    PENDING = "pending"

    @classmethod
    def _missing_(cls, _: object) -> "Status":
        """Handle the enum when the value is missing.

        Returns:
            value: Status.UNKNOWN.
        """
        return cls(cls.UNKNOWN)


class RecordType(str, Enum):
    """Represent the DNS record types.

    Attributes:
        A: A
        AAAA: AAAA
        CNAME: CNAME
        MX: MX
        DKIM: DKIM
        SPF: SPF
        DMARC: DMARC
        TXT: TXT
        CAA: CAA
        SRV: SRV
        SVCB: SVCB
        HTTPS: HTTPS
        PTR: PTR
        SOA: SOA
        NS: NS
        DS: DS
        DNSKEY: DNSKEY
    """

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    DKIM = "DKIM"
    SPF = "SPF"
    DMARC = "DMARC"
    TXT = "TXT"
    CAA = "CAA"
    SRV = "SRV"
    SVCB = "SVCB"
    HTTPS = "HTTPS"
    PTR = "PTR"
    SOA = "SOA"
    NS = "NS"
    DS = "DS"
    DNSKEY = "DNSKEY"


class RecordClass(str, Enum):
    """Represent the DNS record classes.

    Attributes:
        IN: IN
    """

    IN = "IN"


class Record(pydantic.BaseModel):
    """DNS record.

    Attributes:
        domain: the domain name.
        host_label: host label.
        ttl: TTL.
        record_class: DNS record class.
        record_type: DNS record type.
        record_data: DNS record value (pydantic.IPvAnyAddress for A/AAAA, str otherwise).
    """

    domain: str = pydantic.Field(min_length=1)
    host_label: str = pydantic.Field(min_length=1)
    ttl: int
    record_class: RecordClass = RecordClass.IN
    record_type: RecordType
    record_data: str | pydantic.IPvAnyAddress

    @pydantic.field_serializer(
        "domain",
        "host_label",
        "ttl",
        "record_class",
        "record_type",
        "record_data",
    )
    def serialize_value(self, value: RecordClass | RecordType | str | int | None) -> str | None:
        """Serialize value.

        Args:
            value: input value

        Returns:
            serialized value
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        return str(value.value)

    @pydantic.model_validator(mode="after")
    def validate_model(self) -> "Record":
        """Validate the model.

        Returns:
            A validated Record model

        Raises:
            ValueError: if there is an issue in the model data
        """
        value = self.record_data
        record_type = self.record_type
        if record_type in (RecordType.A, RecordType.AAAA):
            if isinstance(value, pydantic.networks.IPvAnyAddress):
                return self
            if isinstance(value, str):
                try:
                    # mypy is confused by the fact that pydantic interfaces
                    # an external class
                    pydantic.networks.IPvAnyAddress(value)  # type: ignore
                except ValueError as e:
                    raise ValueError(
                        "record_data must be a valid IP address for record_type A or AAAA"
                    ) from e
            else:
                raise ValueError(
                    "record_data must be a string"
                    "or pydantic.IPvAnyAddress for record_type A or AAAA"
                )
        # For other record types, ensure it's a string
        if not isinstance(value, str):
            raise ValueError("record_data must be a string for non-A/AAAA record types")
        return self


class RecordRequest(pydantic.BaseModel):
    """DNS record requested.

    Attributes:
        uuid: UUID for this request.
        status: status for the domain request.
        description: status description for the domain request.
        record: the actual requested DNS record.
    """

    uuid: uuid_module.UUID
    status: Status | None = None
    description: str | None = None
    record: Record | None = None

    @pydantic.model_validator(mode="after")
    def validate_model(self) -> "RecordRequest":
        """Validate the model.

        Returns:
            A validated RecordRequest model

        Raises:
            ValueError: if there is an issue in the model data
        """
        if self.record is None:
            if self.status is None:
                raise ValueError("A record request must have a status if no record is defined")
        return self

    def serialize_as_response(self) -> dict[str, str]:
        """Serialize the RecordRequest as a response.

        Returns:
            The serialized model as a response to a request.
        """
        return self.model_dump(exclude={"record"})

    def serialize_as_request(self) -> dict[str, str]:
        """Serialize the RecordRequest as a request.

        Returns:
            The serialized model as a request.
        """
        request = self.model_dump(exclude={"status", "description", "record"})
        if self.record:
            record = self.record.model_dump()
            request.update(record)
        return request

    @pydantic.field_serializer("uuid")
    def serialize_uuid(self, value: uuid_module.UUID) -> str:
        """Serialize value.

        Args:
            value: input value

        Returns:
            serialized value
        """
        return str(value)


class DNSRecordBase(ops.Object):
    """Base class for the DNS relation."""

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @staticmethod
    def _handle_relation_data(data: dict[str, typing.Any]) -> list[RecordRequest]:
        """Transform relation data into a list of RecordRequest.

        Args:
            data: relation data

        Returns:
            list of RecordRequest
        """
        # Regroup data for each entry based on the uuid
        entries: dict[str, dict[str, typing.Any]] = collections.defaultdict(dict)
        for entry in data["dns_entries"]:
            entries[entry["uuid"]] |= entry

        # Create a record for each entry
        for entry in entries.values():
            try:
                # This works based on the fact that pydantic will ignore extra fields in the input
                entry["record"] = Record.model_validate(entry)
            except pydantic.ValidationError:
                # If we could not create a record, this is not an issue, let's just continue
                continue

        # Create a record request for each entry
        rr_entries: list[RecordRequest] = []
        for entry in entries.values():
            try:
                rr = RecordRequest.model_validate(entry)
                rr_entries.append(rr)
            except pydantic.ValidationError:
                # If we could not create a record request,
                # this is not an issue, let's just continue
                continue

        return rr_entries

    def get_relation_data(self) -> list[RecordRequest] | None:
        """Retrieve the remote relation data.

        Returns:
            the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            return None
        relation_data: ops.RelationDataContent = relation.data[relation.app]
        return self._handle_relation_data({k: json.loads(v) for k, v in relation_data.items()})


class DNSRecordRequires(DNSRecordBase):
    """Requirer side of the DNS requires relation."""

    def __init__(
        self,
        charm: ops.CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
        secret_label: str = DEFAULT_SECRET_LABEL,
    ) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
            secret_label: the label used for the secret.
        """
        super().__init__(charm, relation_name)
        self.secret_label = secret_label

        try:
            self.model.get_secret(label=secret_label)
        except ops.SecretNotFoundError:
            charm.app.add_secret({"namespace": str(uuid_module.uuid4())}, label=secret_label)

    @staticmethod
    def _create_record_request(
        namespace: uuid_module.UUID,
        data: typing.Iterable[str] | str,
        *,
        status: str = str(Status.UNKNOWN),
        description: str = "",
    ) -> RecordRequest:
        """Create a new RecordRequest.

        Args:
            namespace: uuid namespace for the request
            data: Iterable or string with the information
            status: Optional status
            description: Optional description

        Return:
            A newly created recordRequest

        Raise:
            CreateRecordRequestError: when failing to create the RecordRequest
        """
        try:
            if isinstance(data, str):
                data = tuple(data.split())
            data = list(itertools.islice(data, 6))
            if len(data) < 6:
                raise CreateRecordRequestError(f"Incorrect input: {data}")
            host_label, domain, ttl, record_class, record_type, record_data = data
            return RecordRequest.model_validate(
                {
                    "uuid": uuid_module.uuid5(
                        namespace,
                        " ".join(
                            (host_label, domain, ttl, record_class, record_type, record_data)
                        ),
                    ),
                    "record": Record.model_validate(
                        {
                            "host_label": host_label,
                            "domain": domain,
                            "ttl": int(ttl),
                            "record_class": record_class,
                            "record_type": record_type,
                            "record_data": record_data,
                        }
                    ),
                    "status": status,
                    "description": description,
                }
            )
        except ValueError as e:
            raise CreateRecordRequestError(f"Incorrect input: {data}") from e

    def create_record_request(
        self,
        data: typing.Iterable[str] | str,
        *,
        status: str = str(Status.UNKNOWN),
        description: str = "",
    ) -> RecordRequest:
        """Create a new RecordRequest.

        Args:
            data: Iterable or string with the information
            status: Optional status
            description: Optional description

        Return:
            A newly created recordRequest

        Raise:
            CreateRecordRequestError: when failing to create the RecordRequest
        """
        try:
            secret: ops.Secret = self.model.get_secret(label=self.secret_label)
            secret_content: dict[str, str] = secret.get_content()
        except ops.SecretNotFoundError as e:
            raise CreateRecordRequestError("Namespace not found !") from e
        return self._create_record_request(
            uuid_module.UUID(secret_content["namespace"]),
            data,
            status=status,
            description=description,
        )

    def update_relation_data(
        self,
        record_requests: list[RecordRequest],
    ) -> None:
        """Update the relation data.

        Args:
            record_requests: list of RecordRequests
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            return
        dns_entries: list[dict[str, str]] = [rr.serialize_as_request() for rr in record_requests]
        relation_data: dict[str, str] = {"dns_entries": json.dumps(dns_entries)}
        relation.data[self.charm.model.app].update(relation_data)


class DNSRecordProvides(DNSRecordBase):
    """Provider side of the DNS record relation."""

    def update_relation_data(
        self,
        record_requests: list[RecordRequest],
    ) -> None:
        """Update the relation data.

        Args:
            record_requests: list of RecordRequests
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            return
        dns_entries: list[dict[str, str]] = [rr.serialize_as_response() for rr in record_requests]
        relation_data: dict[str, str] = {"dns_entries": json.dumps(dns_entries)}
        relation.data[self.charm.model.app].update(relation_data)
