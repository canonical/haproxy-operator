# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""gateway-api-integrator charm base exceptions."""


class CharmStateValidationBaseError(Exception):
    """Exception raised when charm state data validation failed."""


class ResourceManagementBaseError(Exception):
    """Exception raised when managing k8s resources."""