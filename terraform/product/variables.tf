# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_uuid" {
  description = "ID of the model to deploy to"
  type        = string
  default     = ""
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
  default = {}
}

variable "hacluster" {
  type = object({
    app_name = optional(string, "hacluster")
    channel  = optional(string, "2.4/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = null
}

variable "keepalived" {
  type = object({
    app_name = optional(string, "keepalived")
    channel  = optional(string, "latest/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = null
  validation {
    condition     = (var.hacluster == null || var.keepalived == null)
    error_message = "hacluster and keepalived cannot both be set."
  }
}

variable "grafana_agent" {
  type = object({
    app_name = optional(string, "grafana-agent")
    channel  = optional(string, "2/stable")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = {}
}
