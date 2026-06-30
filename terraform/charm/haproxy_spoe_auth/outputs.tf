# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy_spoe_auth.name
}

output "application" {
  description = "The deployed haproxy-spoe-auth application object."
  value       = juju_application.haproxy_spoe_auth
}

output "provides" {
  value = {
    spoe_auth = "spoe-auth"
  }
}

output "requires" {
  value = {
    oauth = "oauth"
  }
}
