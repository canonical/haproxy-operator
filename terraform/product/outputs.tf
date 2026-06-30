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
    oauth = "oauth"
  }
}

output "haproxy_spoe_auth_app_names_map" {
  description = "Map of hostnames to haproxy-spoe-auth application name."
  value       = { for hostname, spoe_auth in module.haproxy_spoe_auth : hostname => spoe_auth.app_name }
}

output "models" {
  description = "Map of model key to its model_uuid and deployed components."
  value = {
    haproxy = {
      model_uuid = var.model_uuid
      components = merge(
        {
          haproxy                              = module.haproxy.application
          grafana_agent                        = juju_application.grafana_agent
          haproxy_ddos_protection_configurator = module.haproxy_ddos_protection_configurator.application
        },
        {
          for hostname, spoe_auth in module.haproxy_spoe_auth :
          "haproxy_spoe_auth_${spoe_auth.app_name}" => spoe_auth.application
        },
        {
          for hostname, idp in juju_application.oauth_external_idp_integrator :
          "oauth_external_idp_integrator_${idp.name}" => idp
        }
      )
    }
  }
}

output "metadata" {
  description = "Deployment metadata."
  value = {
    version = var.metadata_version
  }
}
