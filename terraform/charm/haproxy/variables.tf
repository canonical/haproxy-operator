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

variable "endpoint_bindings" {
  description = "Endpoint bindings for the haproxy application. Set of objects mapping an endpoint name to a network space. Leave null to use the model's default bindings."
  type = set(object({
    endpoint = optional(string)
    space    = string
  }))
  default = null
}

variable "expose" {
  description = "Expose configuration for the haproxy application. The default of {} reproduces the always-exposed behavior (an empty expose block). Set to null to not expose the application, or set cidrs/endpoints/spaces to restrict access."
  type = object({
    cidrs     = optional(string)
    endpoints = optional(string)
    spaces    = optional(string)
  })
  default = {}
}

variable "machines" {
  description = "Set of existing machines to place the haproxy units on. Mutually exclusive with units; leave null to let Juju place units according to the units count."
  type        = set(string)
  default     = null
}

variable "model_uuid" {
  description = "ID of the Juju model to deploy to."
  type        = string
}

variable "resources" {
  description = "Charm resources for the haproxy application. Map of resource name to a CharmHub revision number or a custom OCI image URL."
  type        = map(string)
  default     = {}
}

variable "revision" {
  description = "Revision of the haproxy charm."
  type        = number
  default     = null
}

variable "storage_directives" {
  description = "Storage directives (constraints) for the haproxy application. Map of the storage label defined by the charm to a directive of the form [<pool>,][<count>,][<size>]."
  type        = map(string)
  default     = {}
}

variable "units" {
  description = "Number of haproxy units. If hacluster is enabled, it is recommended to use a value > 3 to ensure a quorum."
  type        = number
  default     = 1
}


