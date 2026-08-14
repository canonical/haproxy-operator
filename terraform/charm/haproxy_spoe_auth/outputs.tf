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
  description = "Map of provided endpoints."
  value = {
    spoe_auth = {
      kind       = "endpoint"
      name       = juju_application.haproxy_spoe_auth.name
      endpoint   = "spoe-auth"
      controller = null
    }
  }
}

output "requires" {
  description = "Map of required endpoints."
  value = {
    oauth = {
      kind       = "endpoint"
      name       = juju_application.haproxy_spoe_auth.name
      endpoint   = "oauth"
      controller = null
    }
  }
}
