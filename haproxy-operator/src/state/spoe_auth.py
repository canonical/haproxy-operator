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
    """Exception raised when there is an error validating spoe relations."""


class SpoeAuthInformation(SpoeAuthProviderAppData):
    """Component containing information about a spoe-auth relation.

    Attrs:
      id: Unique identifier for the spoe-auth relation.
      unit_addresses: List of IP addresses of the spoe agents.
    """

    id: int
    unit_addresses: list[IPvAnyAddress]

    @classmethod
    def from_requirer(cls, spoe_auth_requirer: SpoeAuthRequirer) -> list[Self]:
        """Get list of spoe-auth information from the SpoeAuthRequirer.

        Args:
          charm: The haproxy charm.
          spoe_auth_requirer: SpoeAuthRequirer for the endpoint.

        Raises:
            SpoeAuthValidationError: When there is an error validating a spoe relation.

        Returns:
            List of SpoeAuthInformation
        """
        response = []

        for relation in spoe_auth_requirer.relations:
            try:
                app_data = spoe_auth_requirer.get_provider_application_data(relation)
            except (DataValidationError, SpoeAuthInvalidRelationDataError) as ex:
                raise SpoeAuthValidationError(
                    f"spoe validation error for {relation.app.name}"
                ) from ex

            try:
                requirer_units_data = spoe_auth_requirer.get_provider_unit_data(relation)
            except DataValidationError as ex:
                raise SpoeAuthValidationError(
                    f"Spoe validation error for {relation.app.name}"
                ) from ex

            unit_addresses = [unit_data.address for unit_data in requirer_units_data]
            spoe_auth_information = cls(
                **app_data.model_dump(),
                unit_addresses=unit_addresses,
                id=relation.id,
            )
            response.append(spoe_auth_information)
        return response
