# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy_ddos_protection_configurator.name
}

output "provides" {
  value = {
    ddos_protection = "ddos-protection"
  }
}

output "requires" {
  value = {}
}
