# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "juju_model_name" {
  description = "Name of the juju model."
  type        = string
}

variable "haproxy_application_name" {
  description = "Application name of the deployed haproxy charm."
  type        = string
}

variable "haproxy_charm_channel" {
  description = "Revision of the haproxy charm."
  type        = string
}

variable "haproxy_charm_revision" {
  description = "Revision of the haproxy charm."
  type        = number
}

variable "haproxy_charm_base" {
  description = "Base of the haproxy charm."
  type        = string
}


variable "haproxy_config" {
  description = "Haproxy charm config."
  type        = map(string)
}

variable "haproxy_units" {
  description = "Number of haproxy units. If hacluster is enabled, it is recommended to use a value > 3 to ensure a quorum."
  type        = number
}

variable "haproxy_constraints" {
  description = "Haproxy charm constraints."
  type        = string
}

# hacluster
variable "use_hacluster" {
  description = "Whether to use hacluster for active/passive."
  type        = bool
}

variable "hacluster_charm_revision" {
  description = "Revision of the hacluster charm."
  type        = number
}

variable "hacluster_charm_channel" {
  description = "Channel of the hacluster charm."
  type        = string
}

variable "hacluster_config" {
  description = "Hacluster charm config."
  type        = map(string)
}

# grafana-agent
variable "use_grafana_agent" {
  description = "Whether to use cos-agent to forward metrics to the COS stack."
  type        = bool
}

variable "grafana_agent_charm_channel" {
  description = "Channel of the cos-agent charm."
  type        = string
}

variable "grafana_agent_charm_revision" {
  description = "Revision of the cos-agent charm."
  type        = number
}

variable "grafana_agent_config" {
  description = "Grafana agent charm config."
  type        = map(string)
}