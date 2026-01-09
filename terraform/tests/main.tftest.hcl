# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "latest/edge"
}

run "basic_deploy" {
  assert {
    condition     = module.haproxy_product.grafana_agent == "grafana-agent"
    error_message = "grafana_agent app_name did not match expected"
  }

  assert {
    condition     = length(module.haproxy_product.haproxy_spoe_auth_app_names_map) == 2
    error_message = "Two haproxy-spoe-auth should be deployed"
  }
}
