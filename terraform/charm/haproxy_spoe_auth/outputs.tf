# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy_spoe_auth.name
}

output "provides" {
  value = {
    spoe_auth       = "spoe-auth"
  }
}
