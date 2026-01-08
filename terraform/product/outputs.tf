# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "grafana_agent" {
  description = "Name of the deployed grafana-agent application."
  value       = juju_application.grafana_agent.name
}

output "haproxy_app_name" {
  description = "Name of the deployed haproxy application."
  value       = module.haproxy.app_name
}

output "provides" {
  value = {
    ingress          = "ingress"
    haproxy_route    = "haproxy-route"
    logging_provider = "logging-provider"
  }
}

output "requires" {
  value = {
    reverseproxy                = "reverseproxy"
    certificates                = "certificates"
    receive_ca_certs            = "receive-ca-certs"
    metrics_endpoint            = "metrics-endpoint"
    send_remote_write           = "send-remote-write"
    grafana_dashboards_consumer = "grafana-dashboards-consumer"
  }
}

output "haproxy_spoe_auth_provides" {
  value = {
    spoe_auth = "spoe-auth"
  }
}

output "haproxy_spoe_auth_app_names_map" {
  description = "Name of the deployed haproxy-spoe-auth applications per hostname."
  value       = { for k, m in module.haproxy_spoe_auth : k => m.app_name }
}
