#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state for database information."""

import ops
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from pydantic import Field
from pydantic.dataclasses import dataclass

DATABASE_RELATION = "database"


class DatabaseRelationMissingError(Exception):
    """Raised when the database relation is missing."""


class DatabaseRelationNotReadyError(Exception):
    """Raised when the database relation is not ready."""


@dataclass
class DatabaseInformation:
    """Charm state for database information.

    Attributes:
        username: Database username.
        host: Database host.
        port: Database port.
        password: Database password.
        database_name: Database name.
    """

    username: str = Field()
    host: str = Field()
    port: int = Field(gt=1, lt=65536)
    password: str = Field()
    database_name: str = Field()

    @property
    def haproxy_route_policy_snap_configuration(self) -> dict[str, str]:
        """Return snap configuration keys and values."""
        return {
            "database-host": self.host,
            "database-port": str(self.port),
            "database-user": self.username,
            "database-password": self.password,
            "database-name": self.database_name,
        }

    @classmethod
    def from_requirer(
        cls, charm: ops.CharmBase, database: DatabaseRequires
    ) -> "DatabaseInformation":
        """Create a DatabaseInformation charm state.

        Returns:
            DatabaseInformation: The database information.

        Raises:
            DatabaseRelationMissingError: If the database relation is missing.
            DatabaseRelationNotReadyError: If the database relation is not ready.
        """
        relation = charm.model.get_relation(database.relation_name)
        if relation is None:
            raise DatabaseRelationMissingError("Database relation not found.")

        relation_data = database.fetch_relation_data()[relation.id]
        endpoint = relation_data.get("endpoints")
        username = relation_data.get("username")
        password = relation_data.get("password")

        if endpoint is None or username is None or password is None:
            raise DatabaseRelationNotReadyError("Incomplete database relation data.")
        host, _, port = endpoint.partition(":")
        if not port:
            port = "5432"

        return cls(
            username=username,
            password=password,
            database_name=charm.app.name,
            host=host,
            port=int(port),
        )
