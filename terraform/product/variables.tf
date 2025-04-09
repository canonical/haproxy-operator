
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model" {
  description = "Reference to the k8s Juju model to deploy application to."
  type        = string
}

variable "haproxy" {
  type = object({
    app_name    = optional(string, "haproxy")
    channel     = optional(string, "2.8/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
  })
}

variable "hacluster" {
  type = object({
    enabled  = optional(bool, false)
    channel  = optional(string, "2.4/edge")
    config   = optional(map(string), {})
    revision = optional(number)
  })
}

variable "grafana-agent" {
  type = object({
    enabled  = optional(bool, false)
    channel  = optional(string, "latest/stable")
    config   = optional(map(string), {})
    revision = optional(number)
  })
}
