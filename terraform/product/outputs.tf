# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "grafana_agent" {
  description = "Name of the deployed grafana-agent application."
  value       = juju_application.grafana_agent.name
}

output "provides" {
  value = {
    reverseproxy  = "reverseproxy"
    ingress       = "ingress"
    haproxy_route = "haproxy_route"
    logging_provider = "logging-provider"
  }
}

output "requires" {
  value = {
    metrics_endpoint  = "metrics-endpoint"
    send_remote_write = "send-remote-write"
    grafana_dashboards_consumer = "grafana-dashboards-consumer"
  }
}