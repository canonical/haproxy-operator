# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_providers {
    juju = {
      version = "~> 1.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}


locals {
  protected_hostnames = toset(["one.example.com", "two.example.com"])

  # Only one of the hostnames will have the external idp configured automatically.
  # The other one will require a manual integration by the user of the terraform module.
  protected_hostnames_idp_configuration = {
    "one.example.com" = {
      issuer_url             = "https://login.example.com"
      authorization_endpoint = "https://login.example.com/oauth2/auth"
      jwks_endpoint          = "https://login.example.com/.well-known/jwks.json"
      token_endpoint         = "https://login.example.com/oauth2/token"
      userinfo_endpoint      = "https://login.example.com/userinfo"
      scope                  = "openid profile email"
      client_id              = "clientid1"
      client_secret          = "clientsecret1"
    }
  }
}

data "juju_model" "model" {
  name  = "prod-haproxy-example"
  owner = "admin"
}

module "haproxy_product" {
  source                                = "../product"
  model_uuid                            = data.juju_model.model.uuid
  protected_hostnames                   = local.protected_hostnames
  protected_hostnames_idp_configuration = local.protected_hostnames_idp_configuration
}
