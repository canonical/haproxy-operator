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


