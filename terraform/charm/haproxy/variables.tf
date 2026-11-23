# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy charm."
  type        = string
  default     = "haproxy"
  nullable    = false
}

variable "base" {
  description = "Base of the haproxy charm."
  type        = string
  default     = null
}

variable "channel" {
  description = "Channel of the haproxy charm."
  type        = string
  default     = "3.2/edge"
  nullable    = false
}

variable "config" {
  description = "Haproxy charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Haproxy constraints."
  type        = string
  default     = null
}

variable "machines" {
  description = "Machines to deploy haproxy units to. Takes precedence over units when set."
  type        = set(string)
  default     = []
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
  nullable    = false
}

variable "revision" {
  description = "Revision of the haproxy charm."
  type        = number
  default     = null
}

variable "units" {
  description = "Number of haproxy units. Ignored when machines is set."
  type        = number
  default     = 1
}

