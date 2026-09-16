# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_version = ">= 1.6"
  required_providers {
    juju = {
      version = ">= 1.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

resource "juju_model" "test_model" {
  name = "tf-testing-${formatdate("YYYYMMDDhhmmss", timestamp())}"
}

resource "juju_machine" "test_machine" {
  model_uuid  = juju_model.test_model.uuid
  constraints = "arch=amd64"
}

output "model_uuid" {
  value = juju_model.test_model.uuid
}

output "machine_id" {
  value = juju_machine.test_machine.machine_id
}
