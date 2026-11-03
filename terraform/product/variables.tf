# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "haproxy" {
  type = object({
    app_name    = optional(string, "haproxy")
    channel     = optional(string, "3.2/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@26.04")
    units       = optional(number)
    machines    = optional(set(string))
  })
  default = {}
  validation {
    condition     = var.haproxy.machines == null || var.haproxy.units == null
    error_message = "haproxy machines and units cannot both be set."
  }
}

variable "haproxy_ddos_protection_configurator" {
  description = "Configuration for haproxy-ddos-protection-configurator charm deployment."
  type = object({
    app_name    = optional(string, "haproxy-ddos-protection-configurator")
    channel     = optional(string, "latest/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number, null)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
  })
  default = {}
}

variable "keepalived" {
  type = object({
    app_name = optional(string, "keepalived")
    channel  = optional(string, "latest/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = null
}

variable "metadata_version" {
  description = "Version string reported in the product module 'metadata' output."
  type        = string
  default     = "1.0.0"
}

variable "model_uuid" {
  description = "ID of the model to deploy to"
  type        = string
  default     = ""
}

variable "opentelemetry_collector" {
  description = "Configuration for the opentelemetry-collector subordinate charm deployment."
  type = object({
    app_name = optional(string, "opentelemetry-collector")
    channel  = optional(string, "0.130/stable")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = {}
}

variable "protected_hostnames_configuration" {
  description = <<EOF
Configuration for each protected hostname.
For each hostname, a haproxy-spoe-auth application will be deployed and integrated to haproxy.
Optionally a oauth-external-idp-integrator application can be deployed and integrated to haproxy-spoe-auth.
The hostnames to protect have to be provided through the haproxy_route relation.
EOF
  type = list(object({
    hostname = string
    haproxy_spoe_auth = optional(object({
      # The hostname will be added automatically
      config = optional(map(string), {})
      # A random number will be appended to each app_name
      app_name    = optional(string, "haproxy-spoe-auth")
      channel     = optional(string, "latest/stable")
      constraints = optional(string, "arch=amd64")
      revision    = optional(number)
      base        = optional(string, "ubuntu@24.04")
      units       = optional(number, 1)
    }), {})
    oauth_external_idp_integrator = optional(object({
      # A number will be appended to the app_name
      app_name    = optional(string, "oauth-external-idp-integrator")
      channel     = optional(string, "latest/edge")
      config      = optional(map(string), {})
      constraints = optional(string, "arch=amd64")
      revision    = optional(number)
      base        = optional(string, "ubuntu@22.04")
      units       = optional(number, 1)
    }), null)
  }))
}
