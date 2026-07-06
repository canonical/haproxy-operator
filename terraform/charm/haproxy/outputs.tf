# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy.name
}

output "provides" {
  value = {
    ingress       = "ingress"
    haproxy_route = "haproxy-route"
    cos_agent     = "cos-agent"
    spoe_auth     = "spoe-auth"
  }
}

output "requires" {
  value = {
    certificates     = "certificates"
    receive_ca_certs = "receive-ca-certs"
    reverseproxy     = "reverseproxy"
    ddos_protection  = "ddos-protection"
  }
}
