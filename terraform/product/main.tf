
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "haproxy" {
  name = var.model
}

module "haproxy" {
  source = "../charm"

  model = data.juju_model.haproxy.name

  app_name    = var.haproxy.app_name
  channel     = var.haproxy.channel
  revision    = var.haproxy.revision
  base        = var.haproxy.base
  units       = var.haproxy.units
  constraints = var.haproxy.constraints
  config      = var.haproxy.config

  use_hacluster            = true
  hacluster_charm_channel  = var.hacluster.channel
  hacluster_charm_revision = var.hacluster.revision
  hacluster_config         = var.hacluster.config
}

resource "juju_application" "grafana_agent" {
  name  = "grafana-agent"
  model = data.juju_model.haproxy.name
  units = var.haproxy.units

  charm {
    name     = "grafana-agent"
    revision = var.grafana_agent.revision
    channel  = var.grafana_agent.channel
    base     = var.haproxy.base
  }

  config = var.grafana_agent.config
}

resource "juju_integration" "grafana_agent" {
  model = data.juju_model.haproxy.name

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.provides.cos_agent
  }

  application {
    name     = juju_application.grafana_agent.name
    endpoint = "cos-agent"
  }
}
