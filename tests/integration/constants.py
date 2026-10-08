# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pinned revisions of dependency charms used by the integration tests.

Each constant is annotated with a structured comment that Renovate parses to look up
the latest matching revision on CharmHub for the given channel/base/arch combination and
open a PR when a newer one is available. See the "Dependency management on integration
tests" spec (ISD301) for the full standard.

The variable name MUST end with the suffix `_REVISION`.
"""

# renovate: depName="self-signed-certificates" channel="1/stable" base="22.04" arch="amd64"
SELF_SIGNED_CERTIFICATES_REVISION = 588

# renovate: depName="hydra" channel="latest/edge" base="22.04" arch="amd64"
HYDRA_REVISION = 404

# renovate: depName="kratos" channel="latest/edge" base="22.04" arch="amd64"
KRATOS_REVISION = 574

# renovate: depName="identity-platform-login-ui-operator" channel="latest/edge" base="22.04" arch="amd64"
IDENTITY_PLATFORM_LOGIN_UI_OPERATOR_REVISION = 210

# NOTE: "latest/edge" no longer publishes a 22.04 base for traefik-k8s (only 20.04/26.04
# are currently available). The previous static pin (revision 270) predates this change
# and no longer matches *any* base in this channel. 26.04 is picked here as the actively
# maintained base; see PR description for details.
# renovate: depName="traefik-k8s" channel="latest/edge" base="26.04" arch="amd64"
TRAEFIK_K8S_REVISION = 475

# NOTE: previously deployed without a pinned revision (implicitly tracked channel head).
# renovate: depName="postgresql-k8s" channel="14/edge" base="22.04" arch="amd64"
POSTGRESQL_K8S_REVISION = 971
