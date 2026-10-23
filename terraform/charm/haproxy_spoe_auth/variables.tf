# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy-spoe-auth charm."
  type        = string
  default     = "haproxy-spoe-auth"
}

variable "base" {
  description = "Base of the haproxy-spoe-auth charm."
  type        = string
  default     = "ubuntu@24.04"
}

variable "channel" {
  description = "Channel of the haproxy-spoe-auth charm."
  type        = string
  default     = "latest/edge"
}

variable "config" {
  description = "haproxy-spoe-auth charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "haproxy-spoe-auth constraints."
  type        = string
  default     = "arch=amd64"
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
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
