# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_providers {
    juju = {
      source  = "juju/juju"
      version = ">= 0.16.0"
    }
  }
}

resource "juju_application" "haproxy" {
  name  = var.haproxy_application_name
  model = var.juju_model_name
  units = var.haproxy_units

  charm {
    name     = "haproxy"
    revision = var.haproxy_charm_revision
    channel  = var.haproxy_charm_channel
    base     = var.haproxy_charm_base
  }

  config = var.haproxy_config

  expose {}
}

resource "juju_application" "grafana-agent" {
  count = var.use_grafana_agent ? 1 : 0
  name  = "grafana-agent"
  model = var.juju_model_name
  units = 0

  charm {
    name     = "grafana-agent"
    revision = var.grafana_agent_charm_revision
    channel  = var.grafana_agent_charm_channel
    base     = var.haproxy_charm_base
  }

  config = var.grafana_agent_config
}

resource "juju_integration" "cos-agent" {
  count = var.use_grafana_agent ? 1 : 0
  model = var.juju_model_name

  application {
    name     = juju_application.haproxy.name
    endpoint = "cos-agent"
  }

  application {
    name     = juju_application.grafana-agent.name
    endpoint = "cos-agent"
  }
}

resource "juju_application" "hacluster" {
  count = var.use_hacluster ? 1 : 0
  name  = "hacluster"
  model = var.juju_model_name
  units = 0

  charm {
    name     = "hacluster"
    revision = var.hacluster_charm_revision
    channel  = var.hacluster_charm_channel
    base     = var.haproxy_charm_base
  }

  config = var.hacluster_config
}

resource "juju_integration" "ha" {
  count = var.use_hacluster ? 1 : 0
  model = local.juju_model_name

  application {
    name     = juju_application.haproxy.name
    endpoint = "ha"
  }

  application {
    name     = juju_application.hacluster.name
    endpoint = "ha"
  }
}
