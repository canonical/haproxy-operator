# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  module {
    source = "./product"
  }

  variables {
    model_uuid = run.setup_tests.model_uuid
    protected_hostnames_configuration = [
      {
        hostname = "one.example.com"
        oauth_external_idp_integrator = {
          config = {
            issuer_url             = "https://login.example.com"
            authorization_endpoint = "https://login.example.com/oauth2/auth"
            introspection_endpoint = "https://login.example.com/tokeninfo"
            jwks_endpoint          = "https://login.example.com/.well-known/jwks.json"
            token_endpoint         = "https://login.example.com/oauth2/token"
            userinfo_endpoint      = "https://login.example.com/userinfo"
            scope                  = "openid profile email"
            client_id              = "clientid1"
            client_secret          = "clientsecret1"
          }
        }
      },
      {
        hostname = "two.example.com"
        haproxy_spoe_auth = {
          channel = "latest/edge"
        }
      }
    ]
  }

  assert {
    condition     = output.grafana_agent == "grafana-agent"
    error_message = "grafana_agent app_name did not match expected"
  }

  assert {
    condition     = length(output.haproxy_spoe_auth_app_names_map) == 2
    error_message = "Two haproxy-spoe-auth should be deployed"
  }
}
