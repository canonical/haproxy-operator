<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.6 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | ~> 1.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | ~> 1.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_haproxy"></a> [haproxy](#module\_haproxy) | ../charm/haproxy | n/a |
| <a name="module_haproxy_ddos_protection_configurator"></a> [haproxy\_ddos\_protection\_configurator](#module\_haproxy\_ddos\_protection\_configurator) | ../charm/haproxy_ddos_protection_configurator | n/a |
| <a name="module_haproxy_spoe_auth"></a> [haproxy\_spoe\_auth](#module\_haproxy\_spoe\_auth) | ../charm/haproxy_spoe_auth | n/a |

## Resources

| Name | Type |
|------|------|
| [juju_application.grafana_agent](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_application.oauth_external_idp_integrator](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |
| [juju_integration.grafana_agent](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.haproxy_haproxy_ddos_protection_configurator](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.haproxy_spoe_auth](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |
| [juju_integration.oauth_external_idp_integrator](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/integration) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_grafana_agent"></a> [grafana\_agent](#input\_grafana\_agent) | n/a | <pre>object({<br/>    app_name = optional(string, "grafana-agent")<br/>    channel  = optional(string, "2/stable")<br/>    config   = optional(map(string), {})<br/>    revision = optional(number, null)<br/>  })</pre> | `{}` | no |
| <a name="input_hacluster"></a> [hacluster](#input\_hacluster) | n/a | <pre>object({<br/>    app_name = optional(string, "hacluster")<br/>    channel  = optional(string, "2.4/edge")<br/>    config   = optional(map(string), {})<br/>    revision = optional(number, null)<br/>  })</pre> | `null` | no |
| <a name="input_haproxy"></a> [haproxy](#input\_haproxy) | n/a | <pre>object({<br/>    app_name    = optional(string, "haproxy")<br/>    channel     = optional(string, "2.8/edge")<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, "arch=amd64")<br/>    revision    = optional(number)<br/>    base        = optional(string, "ubuntu@24.04")<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_haproxy_ddos_protection_configurator"></a> [haproxy\_ddos\_protection\_configurator](#input\_haproxy\_ddos\_protection\_configurator) | Configuration for haproxy-ddos-protection-configurator charm deployment. | <pre>object({<br/>    app_name    = optional(string, "haproxy-ddos-protection-configurator")<br/>    channel     = optional(string, "latest/edge")<br/>    config      = optional(map(string), {})<br/>    constraints = optional(string, "arch=amd64")<br/>    revision    = optional(number, null)<br/>    base        = optional(string, "ubuntu@24.04")<br/>    units       = optional(number, 1)<br/>  })</pre> | `{}` | no |
| <a name="input_keepalived"></a> [keepalived](#input\_keepalived) | n/a | <pre>object({<br/>    app_name = optional(string, "keepalived")<br/>    channel  = optional(string, "latest/edge")<br/>    config   = optional(map(string), {})<br/>    revision = optional(number, null)<br/>  })</pre> | `null` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | ID of the model to deploy to | `string` | `""` | no |
| <a name="input_protected_hostnames_configuration"></a> [protected\_hostnames\_configuration](#input\_protected\_hostnames\_configuration) | Configuration for each protected hostname.<br/>For each hostname, a haproxy-spoe-auth application will be deployed and integrated to haproxy.<br/>Optionally a oauth-external-idp-integrator application can be deployed and integrated to haproxy-spoe-auth.<br/>The hostnames to protect have to be provided through the haproxy\_route relation. | <pre>list(object({<br/>    hostname = string<br/>    haproxy_spoe_auth = optional(object({<br/>      # The hostname will be added automatically<br/>      config = optional(map(string), {})<br/>      # A random number will be appended to each app_name<br/>      app_name    = optional(string, "haproxy-spoe-auth")<br/>      channel     = optional(string, "latest/stable")<br/>      constraints = optional(string, "arch=amd64")<br/>      revision    = optional(number)<br/>      base        = optional(string, "ubuntu@24.04")<br/>      units       = optional(number, 1)<br/>    }), {})<br/>    oauth_external_idp_integrator = optional(object({<br/>      # A number will be appended to the app_name<br/>      app_name    = optional(string, "oauth-external-idp-integrator")<br/>      channel     = optional(string, "latest/edge")<br/>      config      = optional(map(string), {})<br/>      constraints = optional(string, "arch=amd64")<br/>      revision    = optional(number)<br/>      base        = optional(string, "ubuntu@22.04")<br/>      units       = optional(number, 1)<br/>    }), null)<br/>  }))</pre> | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_grafana_agent"></a> [grafana\_agent](#output\_grafana\_agent) | Name of the deployed grafana-agent application. |
| <a name="output_haproxy_app_name"></a> [haproxy\_app\_name](#output\_haproxy\_app\_name) | Name of the deployed haproxy application. |
| <a name="output_haproxy_spoe_auth_app_names_map"></a> [haproxy\_spoe\_auth\_app\_names\_map](#output\_haproxy\_spoe\_auth\_app\_names\_map) | Map of hostnames to haproxy-spoe-auth application name. |
| <a name="output_haproxy_spoe_auth_provides"></a> [haproxy\_spoe\_auth\_provides](#output\_haproxy\_spoe\_auth\_provides) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->
