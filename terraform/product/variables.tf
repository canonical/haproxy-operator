# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
variable "model_uuid" {
  description = "ID of the model to deploy to, takes priority over model + model_owner"
  type        = string
  default     = ""
}

variable "model" {
  description = "Reference to the Juju model to deploy application to."
  type        = string
  default     = ""
}

variable "model_owner" {
  description = "ID of the model owner, used in conjunction with model name."
  type        = string
  default     = "admin"
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
    channel  = optional(string, "2.4/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = null
}

variable "keepalived" {
  type = object({
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
    channel  = optional(string, "2/stable")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = {}
}
