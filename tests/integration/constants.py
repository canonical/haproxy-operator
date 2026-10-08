# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pinned revisions of dependency charms used by the integration tests (see ISD301)."""

# renovate: depName="self-signed-certificates" channel="1/stable" base="22.04" arch="amd64"
SELF_SIGNED_CERTIFICATES_REVISION = 588

# renovate: depName="hydra" channel="latest/edge" base="22.04" arch="amd64"
HYDRA_REVISION = 404

# renovate: depName="kratos" channel="latest/edge" base="22.04" arch="amd64"
KRATOS_REVISION = 574

# renovate: depName="identity-platform-login-ui-operator" channel="latest/edge" base="22.04" arch="amd64"
IDENTITY_PLATFORM_LOGIN_UI_OPERATOR_REVISION = 210

# renovate: depName="traefik-k8s" channel="latest/edge" base="26.04" arch="amd64"
TRAEFIK_K8S_REVISION = 475

# renovate: depName="postgresql-k8s" channel="14/edge" base="22.04" arch="amd64"
POSTGRESQL_K8S_REVISION = 971
