
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "model" {
  # Don't fetch the model if model_uuid is provided
  count = var.model_uuid != "" ? 0 : 1
  name  = var.model
  owner = var.model_owner
}

locals {
  model_uuid     = var.model_uuid != "" ? var.model_uuid : element(concat(data.juju_model.model.*.id, tolist([""])), 0)
  use_hacluster  = var.hacluster != null
  use_keepalived = var.keepalived != null
}

module "haproxy" {
  source = "../charm"

  model_uuid  = local.model_uuid
  app_name    = var.haproxy.app_name
  channel     = var.haproxy.channel
  revision    = var.haproxy.revision
  base        = var.haproxy.base
  units       = var.haproxy.units
  constraints = var.haproxy.constraints
  config      = var.haproxy.config

  use_hacluster            = local.use_hacluster
  hacluster_charm_channel  = local.use_hacluster ? var.hacluster.channel : null
  hacluster_charm_revision = local.use_hacluster ? var.hacluster.revision : null
  hacluster_config         = local.use_hacluster ? var.hacluster.config : {}

  use_keepalived            = local.use_keepalived
  keepalived_charm_channel  = local.use_keepalived ? var.keepalived.channel : null
  keepalived_charm_revision = local.use_keepalived ? var.keepalived.revision : null
  keepalived_config         = local.use_keepalived ? var.keepalived.config : {}
}

resource "juju_application" "grafana_agent" {
  name       = "grafana-agent"
  model_uuid = local.model_uuid
  units      = 1

  charm {
    name     = "grafana-agent"
    revision = var.grafana_agent.revision
    channel  = var.grafana_agent.channel
    base     = var.haproxy.base
  }

  config = var.grafana_agent.config
}

resource "juju_integration" "grafana_agent" {
  model_uuid = local.model_uuid

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.provides.cos_agent
  }

  application {
    name     = juju_application.grafana_agent.name
    endpoint = "cos-agent"
  }
}
