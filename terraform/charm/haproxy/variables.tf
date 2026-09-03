# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy charm."
  type        = string
  default     = "haproxy"
}

variable "base" {
  description = "Base of the haproxy charm."
  type        = string
  default     = "ubuntu@24.04"
}

variable "channel" {
  description = "Channel of the haproxy charm."
  type        = string
  default     = "2.8/edge"
}

variable "config" {
  description = "Haproxy charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Haproxy constraints."
  type        = string
  default     = "arch=amd64"
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
}

variable "revision" {
  description = "Revision of the haproxy charm."
  type        = number
  default     = null
}

variable "units" {
  description = "Number of haproxy units. If hacluster is enabled, it is recommended to use a value > 3 to ensure a quorum."
  type        = number
  default     = 1
}
