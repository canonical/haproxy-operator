# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "haproxy" {
  name       = var.app_name
  model_uuid = var.model_uuid
  units      = var.units
  machines   = var.machines

  charm {
    name     = "haproxy"
    revision = var.revision
    channel  = var.channel
    base     = var.base
  }

  config      = var.config
  constraints = var.constraints

  endpoint_bindings  = var.endpoint_bindings
  resources          = var.resources
  storage_directives = var.storage_directives

  dynamic "expose" {
    for_each = var.expose == null ? [] : [var.expose]
    content {
      cidrs     = expose.value.cidrs
      endpoints = expose.value.endpoints
      spaces    = expose.value.spaces
    }
  }
}

resource "juju_application" "keepalived" {
  count      = var.use_keepalived ? 1 : 0
  name       = var.keepalived_app_name
  model_uuid = var.model_uuid
  units      = 1

  charm {
    name     = "keepalived"
    revision = var.keepalived_charm_revision
    channel  = var.keepalived_charm_channel
    base     = var.base
  }

  config = var.keepalived_config
}

resource "juju_integration" "keepalived" {
  count      = var.use_keepalived ? 1 : 0
  model_uuid = var.model_uuid

  application {
    name     = juju_application.haproxy.name
    endpoint = "juju-info"
  }

  application {
    name     = juju_application.keepalived[0].name
    endpoint = "juju-info"
  }
}

resource "juju_application" "hacluster" {
  count      = var.use_hacluster ? 1 : 0
  name       = var.hacluster_app_name
  model_uuid = var.model_uuid
  units      = 1

  charm {
    name     = "hacluster"
    revision = var.hacluster_charm_revision
    channel  = var.hacluster_charm_channel
    base     = var.base
  }

  config = var.hacluster_config
}

resource "juju_integration" "ha" {
  count      = var.use_hacluster ? 1 : 0
  model_uuid = var.model_uuid

  application {
    name     = juju_application.haproxy.name
    endpoint = "ha"
  }

  application {
    name     = juju_application.hacluster[0].name
    endpoint = "ha"
  }
}
