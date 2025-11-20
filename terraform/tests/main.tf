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

module "haproxy-product" {
  source   = "../product"
  model    = "prod-haproxy-example"
}
