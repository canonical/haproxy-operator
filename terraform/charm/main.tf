# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_providers {
    juju = {
      source  = "juju/juju"
      version = ">= 0.19.0"
    }
  }
}

resource "juju_application" "haproxy" {
  name  = var.app_name
  model = var.model
  units = var.units

  charm {
    name     = "haproxy"
    revision = var.revision
    channel  = var.channel
    base     = var.base
  }

  config = var.config

  expose {}
}

resource "juju_application" "hacluster" {
  count = var.use_hacluster ? 1 : 0
  name  = var.hacluster_app_name
  model = var.model
  units = 1

  charm {
    name     = "hacluster"
    revision = var.hacluster_charm_revision
    channel  = var.hacluster_charm_channel
    base     = var.base
  }

  config = var.hacluster_config
}

resource "juju_integration" "ha" {
  count = var.use_hacluster ? 1 : 0
  model = var.model

  application {
    name     = juju_application.haproxy.name
    endpoint = "ha"
  }

  application {
    name     = juju_application.hacluster[0].name
    endpoint = "ha"
  }
}
