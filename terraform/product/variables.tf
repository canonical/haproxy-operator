# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_uuid" {
  description = "ID of the model to deploy to"
  type        = string
  default     = ""
}

variable "haproxy" {
  type = object({
    app_name    = optional(string, "haproxy")
    channel     = optional(string, "2.8/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
  })
  default = {}
}

variable "hacluster" {
  type = object({
    app_name = optional(string, "hacluster")
    channel  = optional(string, "2.4/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = null
}

variable "keepalived" {
  type = object({
    app_name = optional(string, "keepalived")
    channel  = optional(string, "latest/edge")
    config   = optional(map(string), {})
    revision = optional(number, null)
  })
  default = null
  validation {
    condition     = (var.hacluster == null || var.keepalived == null)
    error_message = "hacluster and keepalived cannot both be set."
  }
}

variable "grafana_agent" {
  type = object({
    app_name = optional(string, "grafana-agent")
    channel  = optional(string, "2/stable")
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
