# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy-spoe-auth charm."
  type        = string
  default     = "haproxy-spoe-auth"
  nullable    = false
}

variable "base" {
  description = "Base of the haproxy-spoe-auth charm."
  type        = string
  default     = null
}

variable "channel" {
  description = "Channel of the haproxy-spoe-auth charm."
  type        = string
  default     = "latest/edge"
  nullable    = false
}

variable "config" {
  description = "haproxy-spoe-auth charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "haproxy-spoe-auth constraints."
  type        = string
  default     = null
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
  nullable    = false
}

variable "revision" {
  description = "Revision of the haproxy-spoe-auth charm."
  type        = number
  default     = null
}

variable "units" {
  description = "Number of haproxy-spoe-auth units."
  type        = number
  default     = 1
}
