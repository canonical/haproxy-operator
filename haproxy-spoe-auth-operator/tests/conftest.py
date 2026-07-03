# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Register charm test options."""
    parser.addoption("--charm-file", action="store", help="Charm file to be deployed.")
    # --keep-models is passed by reusable CI workflows; consumed as no-op here.
    # pytest-jubilant v2 uses --no-juju-teardown instead.
    parser.addoption(
        "--keep-models",
        action="store_true",
        default=False,
        help="No-op; kept for CI compatibility. Use --no-juju-teardown instead.",
    )
