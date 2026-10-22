# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

locals {
  use_hacluster  = var.hacluster != null
  use_keepalived = var.keepalived != null

  # Product owns each charm's track; `risk` selects the channel risk solution-wide.
  haproxy_channel                              = "2.8/${var.risk}"
  hacluster_channel                            = "2.4/${var.risk}"
  keepalived_channel                           = "latest/${var.risk}"
  grafana_agent_channel                        = "2/${var.risk}"
  haproxy_ddos_protection_configurator_channel = "latest/${var.risk}"
  haproxy_spoe_auth_channel                    = "latest/${var.risk}"
  oauth_external_idp_integrator_channel        = "latest/${var.risk}"
}
