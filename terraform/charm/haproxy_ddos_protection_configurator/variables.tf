# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "haproxy-ddos-protection-configurator"
}

variable "channel" {
  description = "Channel of the haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "latest/edge"
}

variable "config" {
  description = "haproxy-ddos-protection-configurator charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "haproxy-ddos-protection-configurator constraints."
  type        = string
  default     = "arch=amd64"
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
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

variable "base" {
  description = "Base of the haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "ubuntu@24.04"
}
