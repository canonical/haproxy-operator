# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Application name of the deployed haproxy charm."
  type        = string
  default     = "haproxy"
}

variable "channel" {
  description = "Revision of the haproxy charm."
  type        = string
  default     = "2.8/edge"
}

variable "config" {
  description = "Haproxy charm config."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Name of the juju model."
  type        = string
  default     = "arch=amd64"
}

variable "model" {
  description = "Name of the juju model."
  type        = string
  default     = null
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

variable "base" {
  description = "Base of the haproxy charm."
  type        = string
  default     = "ubuntu@24.04"
}

# hacluster
variable "use_hacluster" {
  description = "Whether to use hacluster for active/passive."
  type        = bool
  default     = false
}

variable "hacluster_app_name" {
  description = "Application name of the hacluster charm."
  type        = string
  default     = "hacluster"
}

variable "hacluster_charm_revision" {
  description = "Revision of the hacluster charm."
  type        = number
  default     = null
}

variable "hacluster_charm_channel" {
  description = "Channel of the hacluster charm."
  type        = string
  default     = "2.4/edge"
}

variable "hacluster_config" {
  description = "Hacluster charm config."
  type        = map(string)
  default     = {}
}
