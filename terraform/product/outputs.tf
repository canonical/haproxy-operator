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

output "haproxy_spoe_auth_app_names_map" {
  description = "Map of hostnames to haproxy-spoe-auth application name."
  value       = { for hostname, spoe_auth in module.haproxy_spoe_auth : hostname => spoe_auth.app_name }
}

output "haproxy_spoe_auth_provides" {
  value = {
    oauth = "oauth"
  }
}

output "metadata" {
  description = "Deployment metadata."
  value = {
    version = var.metadata_version
  }
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

output "provides" {
  description = "Map of provided endpoints."
  value = {
    haproxy_route = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "haproxy-route"
      controller = null
    }
    ingress = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "ingress"
      controller = null
    }
    logging_provider = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "logging-provider"
      controller = null
    }
  }
}

output "requires" {
  description = "Map of required endpoints."
  value = {
    certificates = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "certificates"
      controller = null
    }
    grafana_dashboards_consumer = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "grafana-dashboards-consumer"
      controller = null
    }
    metrics_endpoint = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "metrics-endpoint"
      controller = null
    }
    receive_ca_certs = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "receive-ca-certs"
      controller = null
    }
    reverseproxy = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "reverseproxy"
      controller = null
    }
    send_remote_write = {
      kind       = "endpoint"
      name       = module.haproxy.app_name
      endpoint   = "send-remote-write"
      controller = null
    }
  }
}
