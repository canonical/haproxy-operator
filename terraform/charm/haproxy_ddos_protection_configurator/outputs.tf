# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy_ddos_protection_configurator.name
}

output "application" {
  description = "The deployed haproxy-ddos-protection-configurator application object."
  value       = juju_application.haproxy_ddos_protection_configurator
}

output "provides" {
  value = {
    ddos_protection = "ddos-protection"
  }
}

output "requires" {
  value = {}
}
