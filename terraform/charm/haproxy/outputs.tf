# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value = juju_application.haproxy.name
}

output "application" {
  description = "The deployed haproxy application object."
  value       = juju_application.haproxy
}

output "provides" {
  description = "Map of provided endpoints."
  value = {
    cos_agent = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "cos-agent"
      controller = null
    }
    haproxy_route = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "haproxy-route"
      controller = null
    }
    ingress = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "ingress"
      controller = null
    }
    juju_info = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "juju-info"
      controller = null
    }
  }
}

output "requires" {
  description = "Map of required endpoints."
  value = {
    certificates = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "certificates"
      controller = null
    }
    ddos_protection = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "ddos-protection"
      controller = null
    }
    ha = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "ha"
      controller = null
    }
    receive_ca_certs = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "receive-ca-certs"
      controller = null
    }
    reverseproxy = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "reverseproxy"
      controller = null
    }
    spoe_auth = {
      kind       = "endpoint"
      name       = juju_application.haproxy.name
      endpoint   = "spoe-auth"
      controller = null
    }
  }
}
