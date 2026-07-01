# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "haproxy-ddos-protection-configurator"
}

variable "base" {
  description = "Base of the haproxy-ddos-protection-configurator charm."
  type        = string
  default     = "ubuntu@24.04"
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

variable "endpoint_bindings" {
  description = "Endpoint bindings for the haproxy-ddos-protection-configurator application. Set of objects mapping an endpoint name to a network space. Leave null to use the model's default bindings."
  type = set(object({
    endpoint = optional(string)
    space    = string
  }))
  default = null
}

variable "machines" {
  description = "Set of existing machines to place the haproxy-ddos-protection-configurator units on. Mutually exclusive with units; leave null to let Juju place units according to the units count."
  type        = set(string)
  default     = null
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
}

variable "resources" {
  description = "Charm resources for the haproxy-ddos-protection-configurator application. Map of resource name to a CharmHub revision number or a custom OCI image URL."
  type        = map(string)
  default     = {}
}

variable "revision" {
  description = "Revision of the haproxy-ddos-protection-configurator charm."
  type        = number
  default     = null
}

variable "storage_directives" {
  description = "Storage directives (constraints) for the haproxy-ddos-protection-configurator application. Map of the storage label defined by the charm to a directive of the form [<pool>,][<count>,][<size>]."
  type        = map(string)
  default     = {}
}

variable "units" {
  description = "Number of haproxy-ddos-protection-configurator units."
  type        = number
  default     = 1
}
