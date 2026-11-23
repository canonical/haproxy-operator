# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

locals {
  use_keepalived = var.keepalived != null

  # Product owns each charm's track; `risk` selects the channel risk solution-wide.
  haproxy_channel                              = "3.2/${var.risk}"
  keepalived_channel                           = "latest/${var.risk}"
  opentelemetry_collector_channel              = "0.130/${var.risk}"
  haproxy_ddos_protection_configurator_channel = "latest/${var.risk}"
  haproxy_spoe_auth_channel                    = "latest/${var.risk}"
  oauth_external_idp_integrator_channel        = "latest/${var.risk}"
}
