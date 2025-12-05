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
from pydantic import IPvAnyAddress

from .exception import CharmStateValidationBaseError

logger = logging.getLogger(__name__)


class SpoeAuthValidationError(CharmStateValidationBaseError):
    """TODO."""


class SpoeAuthInformation(SpoeAuthProviderAppData):
    """JAVI."""

    # TODO for now, this is coupled to the relation pydantic models.
    id: int
    unit_addresses: list[IPvAnyAddress]

    @classmethod
    def from_requirer(cls, spoe_auth_requirer: SpoeAuthRequirer) -> list[Self]:
        """JAVI."""
        # JAVI. Returning optionally None is probably not so nice. Review this.
        response = []

        for relation in spoe_auth_requirer.relations:
            try:
                app_data = spoe_auth_requirer.get_provider_application_data(relation)
            except (DataValidationError, SpoeAuthInvalidRelationDataError) as ex:
                raise SpoeAuthValidationError from ex

            if not app_data:
                continue

            try:
                requirer_units_data = spoe_auth_requirer.get_provider_unit_data(relation)
            except DataValidationError as ex:
                raise SpoeAuthValidationError from ex

            unit_addresses = [unit_data.address for unit_data in requirer_units_data]
            spoe_auth_information = cls(
                **app_data.dict(),
                unit_addresses=unit_addresses,
                id=relation.id,
            )
            response.append(spoe_auth_information)
        return response
