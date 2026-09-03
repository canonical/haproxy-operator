# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
locals {
  use_hacluster  = var.hacluster != null
  use_keepalived = var.keepalived != null
}

module "haproxy" {
  source = "../charm/haproxy"

  model_uuid  = var.model_uuid
  app_name    = var.haproxy.app_name
  channel     = var.haproxy.channel
  revision    = var.haproxy.revision
  base        = var.haproxy.base
  units       = var.haproxy.units
  constraints = var.haproxy.constraints
  config      = var.haproxy.config
}

resource "juju_application" "hacluster" {
  count      = local.use_hacluster ? 1 : 0
  name       = var.hacluster.app_name
  model_uuid = var.model_uuid
  units      = 0

  charm {
    name     = "hacluster"
    revision = var.hacluster.revision
    channel  = var.hacluster.channel
    base     = var.haproxy.base
  }

  config = var.hacluster.config
}

resource "juju_integration" "ha" {
  count      = local.use_hacluster ? 1 : 0
  model_uuid = var.model_uuid

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.requires.ha.endpoint
  }

  application {
    name     = juju_application.hacluster[0].name
    endpoint = "ha"
  }
}

resource "juju_application" "keepalived" {
  count      = local.use_keepalived ? 1 : 0
  name       = var.keepalived.app_name
  model_uuid = var.model_uuid
  units      = 0

  charm {
    name     = "keepalived"
    revision = var.keepalived.revision
    channel  = var.keepalived.channel
    base     = var.haproxy.base
  }

  config = var.keepalived.config
}

resource "juju_integration" "keepalived" {
  count      = local.use_keepalived ? 1 : 0
  model_uuid = var.model_uuid

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.provides.juju_info.endpoint
  }

  application {
    name     = juju_application.keepalived[0].name
    endpoint = "juju-info"
  }
}

resource "juju_application" "grafana_agent" {
  name       = var.grafana_agent.app_name
  model_uuid = var.model_uuid
  units      = 1

  charm {
    name     = "grafana-agent"
    revision = var.grafana_agent.revision
    channel  = var.grafana_agent.channel
    base     = var.haproxy.base
  }

  config = var.grafana_agent.config
}

resource "juju_integration" "grafana_agent" {
  model_uuid = var.model_uuid

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.provides.cos_agent.endpoint
  }

  application {
    name     = juju_application.grafana_agent.name
    endpoint = "cos-agent"
  }
}

module "haproxy_ddos_protection_configurator" {
  source = "../charm/haproxy_ddos_protection_configurator"

  model_uuid  = var.model_uuid
  app_name    = var.haproxy_ddos_protection_configurator.app_name
  channel     = var.haproxy_ddos_protection_configurator.channel
  revision    = var.haproxy_ddos_protection_configurator.revision
  base        = var.haproxy_ddos_protection_configurator.base
  units       = var.haproxy_ddos_protection_configurator.units
  constraints = var.haproxy_ddos_protection_configurator.constraints
  config      = var.haproxy_ddos_protection_configurator.config
}

resource "juju_integration" "haproxy_haproxy_ddos_protection_configurator" {
  model_uuid = var.model_uuid

  application {
    name     = module.haproxy_ddos_protection_configurator.app_name
    endpoint = module.haproxy_ddos_protection_configurator.provides.ddos_protection.endpoint
  }

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.requires.ddos_protection.endpoint
  }
}

module "haproxy_spoe_auth" {
  source = "../charm/haproxy_spoe_auth"

  for_each = {
    for protected_hostnames_configuration in var.protected_hostnames_configuration :
    protected_hostnames_configuration.hostname => protected_hostnames_configuration.haproxy_spoe_auth
  }

  model_uuid  = var.model_uuid
  app_name    = format("%s%s", each.value.app_name, substr(md5(each.key), 0, 8))
  channel     = each.value.channel
  revision    = each.value.revision
  base        = each.value.base
  units       = each.value.units
  constraints = each.value.constraints
  config      = merge({ hostname = each.key }, each.value.config)
}

resource "juju_integration" "haproxy_spoe_auth" {
  for_each   = module.haproxy_spoe_auth
  model_uuid = var.model_uuid

  application {
    name     = each.value.app_name
    endpoint = each.value.provides.spoe_auth.endpoint
  }

  application {
    name     = module.haproxy.app_name
    endpoint = module.haproxy.requires.spoe_auth.endpoint
  }
}

resource "juju_application" "oauth_external_idp_integrator" {
  for_each = {
    for protected_hostnames_configuration in var.protected_hostnames_configuration :
    protected_hostnames_configuration.hostname => protected_hostnames_configuration.oauth_external_idp_integrator
    if protected_hostnames_configuration.oauth_external_idp_integrator != null
  }

  name       = format("%s%s", each.value.app_name, substr(md5(each.key), 0, 8))
  model_uuid = var.model_uuid
  units      = each.value.units

  charm {
    name     = "oauth-external-idp-integrator"
    revision = each.value.revision
    channel  = each.value.channel
    base     = each.value.base
  }
  config = each.value.config
}

resource "juju_integration" "oauth_external_idp_integrator" {
  for_each = toset([
    for protected_hostnames_configuration in var.protected_hostnames_configuration :
    protected_hostnames_configuration.hostname
    if protected_hostnames_configuration.oauth_external_idp_integrator != null
  ])
  model_uuid = var.model_uuid

  application {
    name     = juju_application.oauth_external_idp_integrator[each.key].name
    endpoint = "oauth"
  }

  application {
    name     = module.haproxy_spoe_auth[each.key].app_name
    endpoint = "oauth"
  }
}
