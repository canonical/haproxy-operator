# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "latest/edge"
}

run "basic_deploy" {
  assert {
    condition     = module.haproxy-product.grafana_agent == "grafana-agent"
    error_message = "haproxy app_name did not match expected"
  }
}
