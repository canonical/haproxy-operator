
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "haproxy" {
  name = var.model
}

module "haproxy" {
  source = "../charm"

  juju_model_name = data.juju_model.haproxy.name

  haproxy_application_name = var.haproxy.app_name
  haproxy_charm_channel    = var.haproxy.channel
  haproxy_charm_revision   = var.haproxy.revision
  haproxy_charm_base       = var.haproxy.base
  haproxy_units            = var.haproxy.units
  haproxy_constraints      = var.haproxy.constraints
  haproxy_config           = var.haproxy.config

  use_hacluster            = var.hacluster.enabled
  hacluster_charm_channel  = var.hacluster.channel
  hacluster_charm_revision = var.hacluster.revision
  hacluster_config         = var.hacluster.config

  use_grafana_agent            = true
  grafana_agent_charm_channel  = var.grafana-agent.channel
  grafana_agent_charm_revision = var.grafana-agent.revision
  grafana_agent_config         = var.grafana-agent.config
}
