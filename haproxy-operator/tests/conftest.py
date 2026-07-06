# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Register charm test options."""
    # --model and --keep-models are passed by reusable CI workflows; consumed as no-ops here.
    # pytest-jubilant v2 uses --juju-model and --no-juju-teardown instead.
    parser.addoption("--model", action="store", default=None, help="No-op; kept for CI compatibility.")
    parser.addoption("--no-deploy", action="store", default=False, help="No-op; kept for CI compatibility.")
    parser.addoption(
        "--keep-models",
        action="store_true",
        default=False,
        help="No-op; kept for CI compatibility. Use --no-juju-teardown instead.",
    )
