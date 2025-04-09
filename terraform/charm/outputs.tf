output "haproxy-application-name" {
  value = juju_application.grafana-agent[0].name
}

output "grafana-agent-application-name" {
  value = juju_application.grafana-agent[0].name
}
