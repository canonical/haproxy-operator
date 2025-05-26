# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy.name
}

output "provides" {
  value = {
    ingress       = "ingress"
    haproxy_route = "haproxy_route"
    cos_agent     = "cos-agent"
  }
}

output "requires" {
  value = {
    certificates = "certificates"
    reverseproxy = "reverseproxy"
  }
}
