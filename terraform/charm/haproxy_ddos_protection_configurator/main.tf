# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "haproxy_ddos_protection_configurator" {
  name       = var.app_name
  model_uuid = var.model_uuid
  units      = var.units

  charm {
    name     = "haproxy-ddos-protection-configurator"
    revision = var.revision
    channel  = var.channel
    base     = var.base
  }

  config      = var.config
  constraints = var.constraints
}
