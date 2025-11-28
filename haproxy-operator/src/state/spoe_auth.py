# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""SPOE authentication state component."""

import logging
import typing

import ops
from charms.haproxy.v0.spoe_auth import (
    DataValidationError,
    SpoeAuthInvalidRelationDataError,
    SpoeAuthProviderAppData,
)
from pydantic import IPvAnyAddress
from pydantic.dataclasses import dataclass

from .exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class SpoeAuthInvalidRelationData(CharmStateValidationBaseError):
    """TODO."""


@dataclass(frozen=True)
class SpoeAuthInformation:
    """JAVI."""

    # TODO for now, this is coupled to the relation pydantic models.
    app_data: SpoeAuthProviderAppData
    unit_addresses: list[IPvAnyAddress]

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "SpoeAuthInformation | None":
        """JAVI."""

        # JAVI. Returning optionally None is probably not so nice. Review this.
        try:
            app_data = charm.spoe_auth_provider.get_data()
        except (DataValidationError, SpoeAuthInvalidRelationDataError) as ex:
            raise SpoeAuthInvalidRelationData from ex

        if not app_data:
            return None

        relation = charm.spoe_auth_provider.relation
        try:
            requirer_units_data = charm.spoe_auth_provider.get_provider_unit_data(relation)
        except DataValidationError as ex:
            raise SpoeAuthInvalidRelationData from ex

        unit_addresses = [unit_data.address for unit_data in requirer_units_data]

        return cls(
            app_data=app_data,
            unit_addresses=unit_addresses,
        )
