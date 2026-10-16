# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "haproxy-ddos-protection-configurator"
  nullable    = false
}

variable "base" {
  description = "Base of the haproxy-ddos-protection-configurator charm."
  type        = string
  default     = null
}

variable "channel" {
  description = "Channel of the haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "latest/edge"
  nullable    = false
}

variable "config" {
  description = "haproxy-ddos-protection-configurator charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "haproxy-ddos-protection-configurator constraints."
  type        = string
  default     = null
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
  nullable    = false
}

variable "revision" {
  description = "Revision of the haproxy-ddos-protection-configurator charm."
  type        = number
  default     = null
}

variable "units" {
  description = "Number of haproxy-ddos-protection-configurator units."
  type        = number
  default     = 1
}
