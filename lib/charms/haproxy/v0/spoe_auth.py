# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=duplicate-code

"""SPOE-auth interface library.

## Getting Started

To get started using the library, you just need to fetch the library using `charmcraft`.

```shell
cd some-charm
charmcraft fetch-lib charms.haproxy.v0.spoe_auth
```

## Using the library as the Requirer

The requirer charm (haproxy-operator) should expose the interface as shown below:

In the `metadata.yaml` of the charm, add the following:

```yaml
requires:
    spoe-auth:
        interface: spoe-auth
        limit: 1
```

Then, to initialise the library:

```python
from charms.haproxy.v0.spoe_auth import SpoeAuthRequirer

class HaproxyCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.spoe_auth = SpoeAuthRequirer(self, relation_name="spoe-auth")

        self.framework.observe(
            self.spoe_auth.on.available, self._on_spoe_auth_available
        )
        self.framework.observe(
            self.spoe_auth.on.removed, self._on_spoe_auth_removed
        )

    def _on_spoe_auth_available(self, event):
        # The SPOE auth configuration is available
        if self.spoe_auth.is_available():
            config = self.spoe_auth.get_config()
            # Use config.spop_port, config.oidc_callback_port, etc.
            ...

    def _on_spoe_auth_removed(self, event):
        # Handle relation broken event
        ...
```

## Using the library as the Provider

The provider charm (SPOE agent) should expose the interface as shown below:

```yaml
provides:
    spoe-auth:
        interface: spoe-auth
```

Then, to initialise the library:

```python
from charms.haproxy.v0.spoe_auth import SpoeAuthProvider

class SpoeAuthCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.spoe_auth = SpoeAuthProvider(self, relation_name="spoe-auth")

        self.framework.observe(
            self.on.config_changed, self._on_config_changed
        )

    def _on_config_changed(self, event):
        # Publish the SPOE auth configuration
        self.spoe_auth.set_config(
            spop_port=9000,
            oidc_callback_port=8080,
            event="on-http-request",
            var_authenticated="txn.authenticated",
            var_redirect_url="txn.redirect_url",
            cookie_name="auth_session",
            oidc_callback_hostname="auth.example.com",
            oidc_callback_path="/oauth2/callback",
        )
```
"""

import json
import logging
from typing import MutableMapping, Optional

from ops import CharmBase, RelationBrokenEvent
from ops.charm import CharmEvents
from ops.framework import EventBase, EventSource, Object
from ops.model import Relation
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# The unique Charmhub library identifier, never change it
LIBID = "a1b2c3d4e5f6789012345678901234ab"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

logger = logging.getLogger(__name__)
SPOE_AUTH_RELATION_NAME = "spoe-auth"


class DataValidationError(Exception):
    """Raised when data validation fails."""


class SpoeAuthInvalidRelationDataError(Exception):
    """Raised when data validation of the spoe-auth relation fails."""


class _DatabagModel(BaseModel):
    """Base databag model.

    Attrs:
        model_config: pydantic model configuration.
    """

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
    def load(cls, databag: MutableMapping) -> "_DatabagModel":
        """Load this model from a Juju json databag.

        Args:
            databag: Databag content.

        Raises:
            DataValidationError: When model validation failed.

        Returns:
            _DatabagModel: The validated model.
        """
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
            logger.error(str(e), exc_info=True)
            raise DataValidationError(msg) from e

    @classmethod
    def from_dict(cls, values: dict) -> "_DatabagModel":
        """Load this model from a dict.

        Args:
            values: Dict values.

        Raises:
            DataValidationError: When model validation failed.

        Returns:
            _DatabagModel: The validated model.
        """
        try:
            logger.info("Loading values from dictionary: %s", values)
            return cls.model_validate(values)
        except ValidationError as e:
            msg = f"failed to validate: {values}"
            logger.debug(msg, exc_info=True)
            raise DataValidationError(msg) from e

    def dump(
        self, databag: Optional[MutableMapping] = None, clear: bool = True
    ) -> Optional[MutableMapping]:
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


class SpoeAuthProviderAppData(_DatabagModel):
    """Configuration model for SPOE authentication provider.

    Attributes:
        spop_port: The port on the agent listening for SPOP.
        oidc_callback_port: The port on the agent handling OIDC callbacks.
        event: The event that triggers SPOE messages (e.g., on-http-request).
        var_authenticated: Name of the variable set by the SPOE agent for auth status.
        var_redirect_url: Name of the variable set by the SPOE agent for IDP redirect URL.
        cookie_name: Name of the authentication cookie used by the SPOE agent.
        oidc_callback_path: Path for OIDC callback.
        oidc_callback_hostname: The hostname HAProxy should route OIDC callbacks to.
    """

    spop_port: int = Field(
        description="The port on the agent listening for SPOP.",
    )
    oidc_callback_port: int = Field(
        description="The port on the agent handling OIDC callbacks.",
    )
    event: str = Field(
        description="The event that triggers SPOE messages (e.g., on-http-request).",
    )
    var_authenticated: str = Field(
        description="Name of the variable set by the SPOE agent for auth status.",
    )
    var_redirect_url: str = Field(
        description="Name of the variable set by the SPOE agent for IDP redirect URL.",
    )
    cookie_name: str = Field(
        description="Name of the authentication cookie used by the SPOE agent.",
    )
    oidc_callback_path: str = Field(
        description="Path for OIDC callback.",
        default="/oauth2/callback",
    )
    oidc_callback_hostname: str = Field(
        description="The hostname HAProxy should route OIDC callbacks to.",
    )


class SpoeAuthProviderDataAvailableEvent(EventBase):
    """SpoeAuthProviderDataAvailableEvent custom event."""


class SpoeAuthProviderDataRemovedEvent(EventBase):
    """SpoeAuthProviderDataRemovedEvent custom event."""


class SpoeAuthProviderEvents(CharmEvents):
    """List of events that the SPOE auth provider charm can leverage.

    Attributes:
        data_available: Emitted when requirer relation data is available.
        data_removed: Emitted when requirer relation is broken.
    """

    data_available = EventSource(SpoeAuthProviderDataAvailableEvent)
    data_removed = EventSource(SpoeAuthProviderDataRemovedEvent)


class SpoeAuthProvider(Object):
    """SPOE auth interface provider implementation.

    Attributes:
        on: Custom events of the provider.
        relations: Related applications.
    """

    on = SpoeAuthProviderEvents()

    def __init__(self, charm: CharmBase, relation_name: str = SPOE_AUTH_RELATION_NAME) -> None:
        """Initialize the SpoeAuthProvider.

        Args:
            charm: The charm that is instantiating the library.
            relation_name: The name of the relation to bind to.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

        self.framework.observe(
            self.charm.on[self.relation_name].relation_changed, self._on_relation_changed
        )
        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken, self._on_relation_broken
        )

    @property
    def relations(self) -> list[Relation]:
        """The list of Relation instances associated with this relation_name.

        Returns:
            list[Relation]: The list of relations.
        """
        return list(self.charm.model.relations[self.relation_name])

    def _on_relation_changed(self, _: EventBase) -> None:
        """Handle relation changed events."""
        self.on.data_available.emit()

    def _on_relation_broken(self, _: EventBase) -> None:
        """Handle relation broken events."""
        self.on.data_removed.emit()

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def set_config(
        self,
        spop_port: int,
        oidc_callback_port: int,
        event: str,
        var_authenticated: str,
        var_redirect_url: str,
        cookie_name: str,
        oidc_callback_hostname: str,
        oidc_callback_path: str = "/oauth2/callback",
    ) -> None:
        """Set the SPOE auth configuration in the application databag.

        Args:
            spop_port: The port on the agent listening for SPOP.
            oidc_callback_port: The port on the agent handling OIDC callbacks.
            event: The event that triggers SPOE messages.
            var_authenticated: Name of the variable for auth status.
            var_redirect_url: Name of the variable for IDP redirect URL.
            cookie_name: Name of the authentication cookie.
            oidc_callback_hostname: The hostname HAProxy should route OIDC callbacks to.
            oidc_callback_path: Path for OIDC callback.
        """
        if not self.charm.unit.is_leader():
            logger.warning("Only the leader unit can set the SPOE auth configuration.")
            return

        config_data = SpoeAuthProviderAppData(
            spop_port=spop_port,
            oidc_callback_port=oidc_callback_port,
            event=event,
            var_authenticated=var_authenticated,
            var_redirect_url=var_redirect_url,
            cookie_name=cookie_name,
            oidc_callback_hostname=oidc_callback_hostname,
            oidc_callback_path=oidc_callback_path,
        )

        for relation in self.relations:
            config_data.dump(relation.data[self.charm.app], clear=True)


class SpoeAuthAvailableEvent(EventBase):
    """SpoeAuthAvailableEvent custom event."""


class SpoeAuthRemovedEvent(EventBase):
    """SpoeAuthRemovedEvent custom event."""


class SpoeAuthRequirerEvents(CharmEvents):
    """List of events that the SPOE auth requirer charm can leverage.

    Attributes:
        available: Emitted when provider configuration is available.
        removed: Emitted when the provider relation is broken.
    """

    available = EventSource(SpoeAuthAvailableEvent)
    removed = EventSource(SpoeAuthRemovedEvent)


class SpoeAuthRequirer(Object):
    """SPOE auth interface requirer implementation.

    Attributes:
        on: Custom events of the requirer.
        relation: The related application.
    """

    on = SpoeAuthRequirerEvents()

    def __init__(self, charm: CharmBase, relation_name: str = SPOE_AUTH_RELATION_NAME) -> None:
        """Initialize the SpoeAuthRequirer.

        Args:
            charm: The charm that is instantiating the library.
            relation_name: The name of the relation to bind to.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

        self.framework.observe(
            self.charm.on[self.relation_name].relation_changed, self._on_relation_changed
        )
        self.framework.observe(
            self.charm.on[self.relation_name].relation_broken, self._on_relation_broken
        )

    @property
    def relation(self) -> Optional[Relation]:
        """The relation instance associated with this relation_name.

        Returns:
            Optional[Relation]: The relation instance, or None if not available.
        """
        relations = self.charm.model.relations[self.relation_name]
        return relations[0] if relations else None

    def _on_relation_changed(self, _: EventBase) -> None:
        """Handle relation changed events."""
        if self.is_available():
            self.on.available.emit()

    def _on_relation_broken(self, _: RelationBrokenEvent) -> None:
        """Handle relation broken events."""
        self.on.removed.emit()

    def is_available(self) -> bool:
        """Check if the SPOE auth configuration is available and valid.

        Returns:
            bool: True if configuration is available and valid, False otherwise.
        """
        if not self.relation:
            return False

        if not self.relation.app:
            return False

        try:
            databag = self.relation.data[self.relation.app]
            if not databag:
                return False
            SpoeAuthProviderAppData.load(databag)
            return True
        except (DataValidationError, KeyError):
            return False

    def get_config(self) -> Optional[SpoeAuthProviderAppData]:
        """Get the SPOE auth configuration from the provider.

        Returns:
            Optional[SpoeAuthProviderAppData]: The SPOE auth configuration,
                or None if not available.

        Raises:
            SpoeAuthInvalidRelationDataError: When configuration data is invalid.
        """
        if not self.relation:
            return None

        if not self.relation.app:
            return None

        try:
            databag = self.relation.data[self.relation.app]
            if not databag:
                return None
            return SpoeAuthProviderAppData.load(databag)  # type: ignore
        except DataValidationError as exc:
            logger.error(
                "spoe-auth data validation failed for relation %s: %s",
                self.relation,
                str(exc),
            )
            raise SpoeAuthInvalidRelationDataError(
                f"spoe-auth data validation failed for relation: {self.relation}"
            ) from exc
