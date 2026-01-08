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


# Todo the haproxy-spoe-auth
variable "protected_hostnames" {
  description = "TODO: haproxy_route Adds one by spoe auth per each..."
  type = set(string)
  default = []
}

variable "haproxy_spoe_auth" {
  type = object({
    # A number will be appended to the app_name
    app_name = optional(string, "haproxy-spoe-auth")
    channel     = optional(string, "latest/stable")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
  })
  default = {}
}

variable "protected_hostnames_configuration" {
  type = map(object({
    issuer_url             = optional(string, "https://login.canonical.com")
    authorization_endpoint = optional(string, "https://login.canonical.com/oauth2/auth")
    # This is not used in OIDC, but requres a value.
    introspection_endpoint = optional(string, "https://login.canonical.com/tokeninfo")
    jwks_endpoint          = optional(string, "https://login.canonical.com/.well-known/jwks.json")
    token_endpoint         = optional(string, "https://login.canonical.com/oauth2/token")
    userinfo_endpoint      = optional(string, "https://login.canonical.com/userinfo")
    scope                  = optional(string, "openid profile email")
    client_id              = string
    client_secret          = string
  }))
  default = {}
}

variable "oauth_external_idp_integrator" {
  type = object({
    # A number will be appended to the app_name
    app_name    = optional(string, "oauth-external-idp-integrator")
    channel     = optional(string, "latest/edge")
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@22.04")
    units       = optional(number, 1)
  })
  default = {}
}
