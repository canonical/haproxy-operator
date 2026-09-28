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

    haproxy = {
      # renovate: depName="haproxy"
      revision = 344
    }

    haproxy_ddos_protection_configurator = {
      # renovate: depName="haproxy-ddos-protection-configurator"
      revision = 206
    }

    protected_hostnames_configuration = [
      {
        hostname = "one.example.com"
        haproxy_spoe_auth = {
          # renovate: depName="haproxy-spoe-auth"
          revision = 186
        }
        oauth_external_idp_integrator = {
          # renovate: depName="oauth-external-idp-integrator"
          revision = 6
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
          # renovate: depName="haproxy-spoe-auth"
          revision = 186
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

  assert {
    condition     = output.models["haproxy"].model_uuid == run.setup_tests.model_uuid
    error_message = "models output should expose the deployed model_uuid"
  }

  assert {
    condition     = contains(keys(output.models["haproxy"].components), "haproxy")
    error_message = "models.components should include the haproxy application"
  }

  assert {
    condition     = output.metadata.version == "1.0.0"
    error_message = "metadata.version should default to 1.0.0"
  }
}

run "haproxy_units_and_machines_are_mutually_exclusive" {
  command = plan

  module {
    source = "./product"
  }

  variables {
    model_uuid = "00000000-0000-0000-0000-000000000000"

    haproxy = {
      units    = 1
      machines = ["0"]
    }

    protected_hostnames_configuration = []
  }

  expect_failures = [var.haproxy]
}

run "haproxy_deploys_on_existing_machine" {
  command = plan

  module {
    source = "./charm/haproxy"
  }

  variables {
    model_uuid = run.setup_tests.model_uuid
    machines   = [run.setup_tests.machine_id]
  }

  assert {
    condition     = output.app_name == "haproxy"
    error_message = "haproxy should be deployed on the existing machine"
  }
}
