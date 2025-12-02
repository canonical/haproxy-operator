# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""SPOE authentication state component."""

import logging
from typing import Self

from charms.haproxy.v0.spoe_auth import (
    DataValidationError,
    SpoeAuthInvalidRelationDataError,
    SpoeAuthProviderAppData,
    SpoeAuthRequirer,
)
from pydantic import BaseModel, IPvAnyAddress

from .exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class SpoeAuthValidationError(CharmStateValidationBaseError):
    """TODO."""


class SpoeAuthInformation(BaseModel):
    """JAVI."""

    # TODO for now, this is coupled to the relation pydantic models.
    app_data: SpoeAuthProviderAppData
    unit_addresses: list[IPvAnyAddress]

    @classmethod
    def from_requirer(cls, spoe_auth_requirer: SpoeAuthRequirer) -> Self | None:
        """JAVI."""
        # JAVI. Returning optionally None is probably not so nice. Review this.
        try:
            app_data = spoe_auth_requirer.get_data()
        except (DataValidationError, SpoeAuthInvalidRelationDataError) as ex:
            raise SpoeAuthValidationError from ex

        if not app_data:
            return None

        relation = spoe_auth_requirer.relation
        try:
            requirer_units_data = spoe_auth_requirer.get_provider_unit_data(relation)
        except DataValidationError as ex:
            raise SpoeAuthValidationError from ex

        unit_addresses = [unit_data.address for unit_data in requirer_units_data]

        return cls(
            app_data=app_data,
            unit_addresses=unit_addresses,
        )
