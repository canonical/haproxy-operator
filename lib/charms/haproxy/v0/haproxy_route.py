"""TODO: Add a proper docstring here.

This is a placeholder docstring for this charm library. Docstrings are
presented on Charmhub and updated whenever you push a new version of the
library.

Complete documentation about creating and documenting libraries can be found
in the SDK docs at https://juju.is/docs/sdk/libraries.

See `charmcraft publish-lib` and `charmcraft fetch-lib` for details of how to
share and consume charm libraries. They serve to enhance collaboration
between charmers. Use a charmer's libraries for classes that handle
integration with their charm.

Bear in mind that new revisions of the different major API versions (v0, v1,
v2 etc) are maintained independently.  You can continue to update v0 and v1
after you have pushed v3.

Markdown is supported, following the CommonMark specification.
"""

# The unique Charmhub library identifier, never change it
LIBID = "08b6347482f6455486b5f5bb4dc4e6cf"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import MutableMapping, Optional

from ops import CharmBase, ModelError, RelationBrokenEvent
from ops.charm import CharmEvents
from ops.framework import EventBase, EventSource, Object, ObjectEvents
from ops.model import Application, Relation
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)
HAPROXY_ROUTE_RELATION_NAME = "haproxy-route"


class DataValidationError(Exception):
    """Raised when data validation fails."""


class HaproxyRouteInvalidRelationDataError(Exception):
    """Rasied when validation of the haproxy-route relation data fails"""


class _DatabagModel(BaseModel):
    """Base databag model."""

    model_config = ConfigDict(
        # tolerate additional keys in databag
        extra="ignore",
        # Allow instantiating this class by field name (instead of forcing alias).
        populate_by_name=True,
        # Custom config key: whether to nest the whole datastructure (as json)
        # under a field or spread it out at the toplevel.
        _NEST_UNDER=None,
    )  # type: ignore
    """Pydantic config."""

    @classmethod
    def load(cls, databag: MutableMapping):
        """Load this model from a Juju databag."""
        nest_under = cls.model_config.get("_NEST_UNDER")
        if nest_under:
            return cls.model_validate(json.loads(databag[nest_under]))

        try:
            data = {
                k: json.loads(v)
                for k, v in databag.items()
                # Don't attempt to parse model-external values
                if k in {(f.alias or n) for n, f in cls.model_fields.items()}
            }
        except json.JSONDecodeError as e:
            msg = f"invalid databag contents: expecting json. {databag}"
            logger.error(msg)
            raise DataValidationError(msg) from e

        try:
            return cls.model_validate_json(json.dumps(data))
        except ValidationError as e:
            msg = f"failed to validate databag: {databag}"
            logger.debug(msg, exc_info=True)
            raise DataValidationError(msg) from e

    @classmethod
    def from_dict(cls, values: dict):
        try:
            return cls.model_validate(values)
        except ValidationError as e:
            msg = f"failed to validate: {values}"
            logger.debug(msg, exc_info=True)
            raise DataValidationError(msg) from e

    def dump(self, databag: Optional[MutableMapping] = None, clear: bool = True):
        """Write the contents of this model to Juju databag.

        Args:
            databag: The databag to write to.
            clear: Whether to clear the databag before writing.

        Returns:
            MutableMapping: The databag.
        """
        if clear and databag:
            databag.clear()

        if databag is None:
            databag = {}
        nest_under = self.model_config.get("_NEST_UNDER")
        if nest_under:
            databag[nest_under] = self.model_dump_json(
                by_alias=True,
                # skip keys whose values are default
                exclude_defaults=True,
            )
            return databag

        dct = self.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        databag.update({k: json.dumps(v) for k, v in dct.items()})
        return databag


class ServerHealthCheck(BaseModel):
    interval: int = Field(description="The interval between health checks.", default=60)
    rise: int = Field(
        description="How many successful health checks before server is considered up.", default=2
    )
    fall: int = Field(
        description="How many failed health checks before server is considered down.", default=3
    )
    paths: list[str] = Field(description="The health check path.", default=[])


# tarpit is not yet implemented
class RateLimitPolicy(Enum):
    """Enum of possible http_route types.

    Attrs:
        DENY: deny a client's HTTP request to return a 403 Forbidden error.
        REJECT: closes the connection immediately without sending a response.
        NOPROXY: disconnects immediately without notifying the client that the connection has been closed.
    """

    DENY = "deny"
    REJECT = "reject"
    SILENT = "silent-drop"


class RateLimit(BaseModel):
    connections_per_minute: int = Field(description="How many connections are allowed per minute.")
    policy: RateLimitPolicy = Field(
        description="Configure the rate limit policy.", default=RateLimitPolicy.DENY
    )


class LoadBalancingAlgorithm(Enum):
    """Enum of possible http_route types.

    Attrs:
        LEASTCONN: The server with the lowest number of connections receives the connection.
        SRCIP: Load balance using the hash of The source IP address.
        ROUNDROBIN: Each server is used in turns, according to their weights.
        COOKIE: Load balance using hash req.cookie(clientid).
    """

    LEASTCONN = "leastconn"
    SRCIP = "source"
    ROUNDROBIN = "roundrobin"
    COOKIE = "cookie"


class LoadBalancingConfiguration(BaseModel):
    algorithm: LoadBalancingAlgorithm = Field(
        description="Configure the load balancing algorithm for the service."
    )
    cookie: Optional[str] = Field(
        description="Only used when algorithm is COOKIE. Define the cookie to load balance on.",
        default=None,
    )


class BandwidthLimit(BaseModel):
    upload: int = Field(description="Upload limit (bytes per seconds).")
    download: int = Field(description="Download limit (bytes per seconds).")


# retry-on is not yet implemented
class Retry(BaseModel):
    count: int = Field(description="How many times should a request retry.")
    interval: int = Field(description="Interval (in seconds) between retries.")
    redispatch: bool = Field(
        description="Whether to redispatch failed requests to another server.", default=False
    )


class TimeoutConfiguration(BaseModel):
    server: int = Field(description="Timeout for requests from haproxy to backend servers.")
    client: int = Field(description="Timeout for client requests to haproxy.")
    queue: int = Field(
        description="Timeout for requests waiting in the queue after server-maxconn is reached."
    )


class HaproxyRewriteMethod(Enum):
    """Enum of possible http_route types.

    Attrs:
        SET_PATH: The server with the lowest number of connections receives the connection.
        SET_QUERY: Load balance using the hash of The source IP address.
        SET_HEADER: Each server is used in turns, according to their weights.
    """

    SET_PATH = "set-path"
    SET_QUERY = "set-query"
    SET_HEADER = "set-header"


class RewriteConfiguration(BaseModel):
    method: HaproxyRewriteMethod = Field(
        description="Which rewrite method to apply.One of set-path, set-query, set-header"
    )
    expression: str = Field(description="Regular expression to use with the rewrite method")
    header: Optional[str] = Field(description="The name of the header to rewrite", default=None)


class RequirerApplicationData(_DatabagModel):
    service: str = Field(description="The name of the service.")
    ports: list[int] = Field(description="The list of ports listening for this service.")
    paths: list[str] = Field(description="The list of paths to route to this service.", default=[])
    subdomains: list[str] = Field(
        description="The list of subdomains to route to this service.", default=[]
    )
    rewrites: list[RewriteConfiguration] = Field(
        description="The list of path rewrite rules.", default=[]
    )
    check: ServerHealthCheck = Field(
        description="Configure health check for the service.",
        default=ServerHealthCheck(interval=60, rise=2, fall=3),
    )
    load_balancing: LoadBalancingConfiguration = LoadBalancingConfiguration(
        algorithm=LoadBalancingAlgorithm.LEASTCONN
    )
    rate_limit: Optional[RateLimit] = Field(
        description="Configure rate limit for the service.", default=None
    )
    bandwidth_limit: Optional[BandwidthLimit] = Field(
        description="Configure bandwidth limit for the service.", default=None
    )
    retry: Optional[Retry] = Field(
        description="Configure retry for incoming requests.", default=None
    )
    deny_paths: list[str] = Field(
        description="Configure path that should not be routed to the backend", default=[]
    )
    timeout: TimeoutConfiguration = Field(
        description="Configure timeout",
        default=TimeoutConfiguration(server=60, client=60, queue=60),
    )
    server_maxconn: Optional[int] = Field(
        description="Configure maximum connection per server", default=None
    )


class HaproxyRouteProviderAppData(_DatabagModel):
    """Ingress application databag schema."""

    url: AnyHttpUrl


class RequirerUnitData(_DatabagModel):
    host: str = Field(description="Hostname or IP address of the unit.")


@dataclass
class HaproxyRouteRequirerData:
    application_data: RequirerApplicationData
    units_data: list[RequirerUnitData]


@dataclass
class HaproxyRouteRequirersData:
    haproxy_route_requirers_data: list[HaproxyRouteRequirerData]


class HaproxyRouteDataAvailableEvent(EventBase):
    """IngressAvailableEvent custom event.

    This event indicates the Ingress provider is available.
    """


class HaproxyRouteProviderEvents(CharmEvents):
    """List of events that the TLS Certificates requirer charm can leverage."""

    data_available = EventSource(HaproxyRouteDataAvailableEvent)


class HaproxyRouteProvider(Object):

    on = HaproxyRouteProviderEvents()

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str = HAPROXY_ROUTE_RELATION_NAME,
    ) -> None:
        """_summary_

        Args:
            charm (CharmBase): _description_
            relation_name (str, optional): _description_. Defaults to HAPROXY_ROUTE_RELATION_NAME.
        """
        super().__init__(charm, relation_name)

        self._relation_name = relation_name
        self.charm = charm
        on = self.charm.on
        self.framework.observe(on[self._relation_name].relation_created, self._configure)
        self.framework.observe(on[self._relation_name].relation_changed, self._configure)
        self.framework.observe(on[self._relation_name].relation_broken, self._configure)

    @property
    def relations(self):
        """The list of Relation instances associated with this endpoint."""
        return list(self.charm.model.relations[self._relation_name])

    def _configure(self, event: EventBase) -> None:
        """_summary_

        Args:
            event (EventBase): _description_
        """
        try:
            if relations := self.relations:
                self.get_data(relations)
                self.on.data_available.emit()  # type: ignore
        except HaproxyRouteInvalidRelationDataError:
            logger.exception("Invalid requirer data, skipping.")
            return

    def get_data(self, relations: list[Relation]) -> HaproxyRouteRequirersData:
        """Fetch the remote (requirer) app and units' databags."""
        haproxy_route_requirers_data: list[HaproxyRouteRequirerData] = []
        for relation in relations:
            try:
                application_data = self._get_requirer_application_data(relation)
                units_data = self._get_requirer_units_data(relation)
                harpoxy_route_requirer_data = HaproxyRouteRequirerData(
                    application_data=application_data, units_data=units_data
                )
                haproxy_route_requirers_data.append(harpoxy_route_requirer_data)
            except DataValidationError as exc:
                logger.exception("haproxy-route data validation failed for relation %s", relation)
                raise HaproxyRouteInvalidRelationDataError(
                    f"haproxy-route data validation failed for relation: {relation}"
                ) from exc
        return HaproxyRouteRequirersData(haproxy_route_requirers_data=haproxy_route_requirers_data)

    def _get_requirer_units_data(self, relation: Relation) -> list[RequirerUnitData]:
        """Fetch and validate the requirer's app databag."""
        requirer_units_data: list[RequirerUnitData] = []

        for unit in relation.units:
            databag = relation.data[unit]
            try:
                data = RequirerUnitData.load(databag)
                requirer_units_data.append(data)
            except DataValidationError:
                logger.exception("Invalid requirer application data for %s", unit)
                raise
        return requirer_units_data

    def _get_requirer_application_data(self, relation: Relation) -> RequirerApplicationData:
        try:
            return RequirerApplicationData.load(relation.data[relation.app])
        except DataValidationError:
            logger.exception("Invalid requirer application data for %s", relation.app.name)
            raise


class HaproxyRouteURLReadyEvent(EventBase):
    """IngressAvailableEvent custom event.

    This event indicates the Ingress provider is available.
    """


class HaproxyRouteURLRemovedEvent(EventBase):
    """IngressAvailableEvent custom event.

    This event indicates the Ingress provider is available.
    """


class HaproxyRouteRequirerEvents(CharmEvents):
    """List of events that the TLS Certificates requirer charm can leverage."""

    ready = EventSource(HaproxyRouteURLReadyEvent)
    removed = EventSource(HaproxyRouteURLRemovedEvent)


class HaproxyRouteRequirer(Object):

    on = HaproxyRouteRequirerEvents()

    def __init__(
        self,
        charm: CharmBase,
        relation_name: str,
        service: str,
        ports: list[int],
        paths: list[str] = [],
        subdomains: list[str] = [],
        check: ServerHealthCheck = ServerHealthCheck(interval=60, rise=2, fall=3, paths=[]),
        load_balancing: LoadBalancingConfiguration = LoadBalancingConfiguration(
            algorithm=LoadBalancingAlgorithm.LEASTCONN, cookie=None
        ),
        rate_limit: Optional[RateLimit] = None,
        bandwidth_limit: Optional[BandwidthLimit] = None,
        retry: Optional[Retry] = None,
        deny_paths: list[str] = [],
        timeout: TimeoutConfiguration = TimeoutConfiguration(server=60, client=60, queue=60),
        server_maxconn: Optional[int] = None,
        host: Optional[str] = None,
    ) -> None:
        """_summary_

        Args:
            charm (CharmBase): _description_
            relation_name (str, optional): _description_. Defaults to HAPROXY_ROUTE_RELATION_NAME.
        """
        super().__init__(charm, relation_name)

        self._relation_name = relation_name
        self.relation = self.model.get_relation(self._relation_name)
        self.charm = charm
        self.app = self.charm.app

        self._service = service
        self._ports = ports
        self._paths = paths
        self._subdomains = subdomains
        self._check = check
        self._load_balancing = load_balancing
        self._rate_limit = rate_limit
        self._bandwidth_limit = bandwidth_limit
        self._retry = retry
        self._deny_paths = deny_paths
        self._timeout = timeout
        self._server_maxconn = server_maxconn
        self._host = host

        on = self.charm.on
        self.framework.observe(on[self._relation_name].relation_created, self._configure)
        self.framework.observe(on[self._relation_name].relation_changed, self._configure)
        self.framework.observe(on[self._relation_name].relation_broken, self._on_relation_broken)

    def _configure(self, _: EventBase) -> None:
        if self.charm.unit.is_leader():
            application_data = self._prepare_application_data()
            self.relation.data[self.app].update(application_data.dump())

        unit_data = self._prepare_unit_data()
        self.relation.data[self.charm.unit].clear()
        self.relation.data[self.charm.unit].update(unit_data.dump())

        if self.relation and self.get_provider_url():
            self.on.ready.emit()

    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        self.on.removed.emit()

    def _prepare_application_data(self) -> RequirerApplicationData:
        try:
            return RequirerApplicationData(
                service=self._service,
                ports=self._ports,
                paths=self._paths,
                subdomains=self._subdomains,
                check=self._check,
                load_balancing=self._load_balancing,
                rate_limit=self._rate_limit,
                bandwidth_limit=self._bandwidth_limit,
                retry=self._retry,
                deny_paths=self._deny_paths,
                timeout=self._timeout,
                server_maxconn=self._server_maxconn,
            )
        except ValidationError as exc:
            logger.exception("Validation error when preparing requirer application data.")
            raise DataValidationError(
                "Validation error when preparing requirer application data."
            ) from exc

    def _prepare_unit_data(self) -> RequirerUnitData:
        host = self._host
        if not host:
            network_binding = self.charm.model.get_binding(self.relation)
            if (
                network_binding is not None
                and (bind_address := network_binding.network.bind_address) is not None
            ):
                host = str(bind_address)
            else:
                logger.error("No host or unit IP available.")
                raise DataValidationError("No host or unit IP available.")
        return RequirerUnitData(host=host)

    def get_provider_url(self) -> Optional[str]:
        """The full ingress URL to reach the current unit.

        Returns None if the URL isn't available yet or is not valid.
        """
        relation = self.relation
        if not relation or not relation.app:
            return None

        # Fetch the provider's app databag
        try:
            databag = relation.data[relation.app]
        except ModelError as e:
            logger.exception("Error reading remote app data.")
            return None

        if not databag:  # not ready yet
            return None

        try:
            return str(HaproxyRouteProviderAppData.load(databag).url)
        except DataValidationError:
            logger.exception("Invalid provider url.")
            return None
