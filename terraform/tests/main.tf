# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_providers {
    juju = {
      version = "~> 1.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

data "juju_model" "model" {
  name  = "prod-haproxy-example"
  owner = "admin"
}

module "haproxy-product" {
  source     = "../product"
  model_uuid = data.juju_model.model.uuid
}
