# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
output "app_name" {
  value = juju_application.haproxy.name
}

output "provides" {
  value = {
    reverseproxy  = "reverseproxy"
    ingress       = "ingress"
    haproxy_route = "haproxy_route"
  }
}
